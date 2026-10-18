"""Shared code of yanll-locate and yanll-obs2json.

yanll owns the JSON side of a location and nothing of NLL's configuration: the input
document becomes an NLLOC_OBS observation file, the NLLoc control file is the model's
template under ${YANLL_CONFIG}/models/<model>/locate.in with its placeholders filled,
and the .hyp NLLoc writes becomes the output document. The configuration contract is
docs/configuration.md.
"""
import datetime as dt
import os
import re

DATA = os.environ.get("YANLL_DATA", "/data")
CONFIG = os.environ.get("YANLL_CONFIG", "/config")
DOCS = "docs/configuration.md"

OBS_HEADER = ("#Station_name Instrument Component P_phase_onset Phase_descriptor First_motion "
              "Date Hour_minute Seconds Err_type Err Err_mag Coda_duration Amplitude\n")
NO_VALUE = "-1.00E+00"

INPUT_KEYS = {"model", "station_corrections", "observations", "event_id", "origin_id"}
OBSERVATION_KEYS = {"station", "channel", "onset", "phase", "first_motion", "time", "quality"}

PLACEHOLDER = re.compile(r"@[A-Z]+@")


class InputError(Exception):
    """The input document is not a valid run: reported to the caller, exit code 2."""


class ConfigError(Exception):
    """The configuration at YANLL_CONFIG is missing or incomplete: exit code 2, the
    message names the file and the documentation."""


# ---------------------------------------------------------------------------
# Configuration directory
# ---------------------------------------------------------------------------

def model_dir(model):
    return os.path.join(CONFIG, "models", model)


def models():
    """The models the configuration offers: the directories under models/ with a
    locate.in. An absent models/ means no configuration is mounted at all."""
    d = os.path.join(CONFIG, "models")
    if not os.path.isdir(d):
        raise ConfigError(f"no models directory in {CONFIG} (YANLL_CONFIG): see {DOCS}")
    return sorted(m for m in os.listdir(d) if os.path.isfile(os.path.join(d, m, "locate.in")))


def check_config(model):
    """The files a location with the model reads, each named when absent."""
    for path in (os.path.join(CONFIG, "stations.txt"),
                 os.path.join(model_dir(model), "locate.in"),
                 os.path.join(model_dir(model), "grid2time.in")):
        if not os.path.isfile(path):
            raise ConfigError(f"{path} missing: see {DOCS}")


def render(template_path, values):
    """The template with every @NAME@ of values replaced, by plain replacement so that
    nothing else in the file is interpreted. A placeholder left over is a configuration
    error: NLLoc would read it as literal text and fail far from the cause."""
    with open(template_path) as fin:
        text = fin.read()
    for name, value in values.items():
        text = text.replace(f"@{name}@", value)
    left = PLACEHOLDER.search(text)
    if left:
        raise ConfigError(f"{template_path}: unknown placeholder {left.group(0)}: see {DOCS}")
    return text


def locate_control(model, obs_path, time_root, out_root, corrections):
    """The NLLoc control file of a run: the model's locate.in with the paths filled in
    and the corrections INCLUDE line active or commented out."""
    cfg = model_dir(model)
    include = ("" if corrections else "#") + "INCLUDE " + os.path.join(cfg, "corrections.in")
    return render(os.path.join(cfg, "locate.in"),
                  {"OBS": obs_path, "TIME": time_root, "OUT": out_root, "CORRECTIONS": include})


# ---------------------------------------------------------------------------
# Input document
# ---------------------------------------------------------------------------

def parse_time(text):
    if not isinstance(text, str):
        raise InputError(f"time must be an ISO 8601 string, got {text!r}")
    try:
        t = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise InputError(f"time {text!r} is not ISO 8601")
    if t.tzinfo is None:
        raise InputError(f"time {text!r} has no UTC designator")
    return t.astimezone(dt.timezone.utc).replace(tzinfo=None)


def time_to_iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def validate_input(doc):
    """Check the document at the boundary and return it with defaults filled in."""
    if not isinstance(doc, dict):
        raise InputError("the input must be a JSON object")
    unknown = set(doc) - INPUT_KEYS
    if unknown:
        raise InputError(f"unknown keys: {', '.join(sorted(unknown))}")
    for key in ("model", "station_corrections", "observations"):
        if key not in doc:
            raise InputError(f"missing key: {key}")
    model = doc["model"]
    # A model is a directory name under models/: checked before it is joined to a path.
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", model):
        raise InputError("model must be a name of letters, digits, '_', '-' and '.'")
    if model not in models():
        # A directory without locate.in is a half-made model, the site's problem, not
        # the caller's.
        if os.path.isdir(model_dir(model)):
            raise ConfigError(f"{os.path.join(model_dir(model), 'locate.in')} missing: see {DOCS}")
        raise InputError(f"unknown model {model!r}: one of {', '.join(models())}")
    if not isinstance(doc["station_corrections"], bool):
        raise InputError("station_corrections must be true or false")
    if doc["station_corrections"] and not os.path.isfile(os.path.join(model_dir(model), "corrections.in")):
        raise InputError(f"model {model} has no station corrections (no corrections.in): set station_corrections to false")
    for key in ("event_id", "origin_id"):
        if key in doc and not (isinstance(doc[key], str) and re.fullmatch(r"[A-Za-z0-9-]+", doc[key])):
            raise InputError(f"{key} must be an alphanumeric string")
    obs = doc["observations"]
    if not isinstance(obs, list) or not obs:
        raise InputError("observations must be a non-empty list")
    out = []
    for i, o in enumerate(obs):
        if not isinstance(o, dict):
            raise InputError(f"observation {i} must be an object")
        unknown = set(o) - OBSERVATION_KEYS
        if unknown:
            raise InputError(f"observation {i}: unknown keys {', '.join(sorted(unknown))}")
        for key in ("station", "phase", "time", "quality"):
            if key not in o:
                raise InputError(f"observation {i}: missing {key}")
        if not isinstance(o["station"], str) or not re.fullmatch(r"[A-Za-z0-9]{1,6}", o["station"]):
            raise InputError(f"observation {i}: station must be 1 to 6 alphanumeric characters")
        if not isinstance(o["phase"], str) or not o["phase"]:
            raise InputError(f"observation {i}: phase must be a non-empty string")
        if not isinstance(o["quality"], int) or isinstance(o["quality"], bool) or not 0 <= o["quality"] <= 9:
            raise InputError(f"observation {i}: quality must be an integer from 0 to 9")
        for key, allowed in (("onset", {"?", "i", "e", "impulsive", "emergent"}), ("first_motion", {"?", "U", "D"})):
            if o.get(key, "?") not in allowed:
                raise InputError(f"observation {i}: {key} must be one of {', '.join(sorted(allowed))}")
        if not isinstance(o.get("channel", "?"), str) or " " in o.get("channel", "?"):
            raise InputError(f"observation {i}: channel must be a string without blanks")
        out.append({"station": o["station"], "channel": o.get("channel", "?"), "onset": o.get("onset", "?"),
                    "phase": o["phase"], "first_motion": o.get("first_motion", "?"),
                    "time": parse_time(o["time"]), "quality": o["quality"]})
    clean = {k: doc[k] for k in INPUT_KEYS if k in doc}
    clean["observations"] = out
    return clean


# ---------------------------------------------------------------------------
# NLLOC_OBS observation file
# ---------------------------------------------------------------------------

def obs_line(o):
    t = o["time"]
    seconds = f"{t.second + t.microsecond / 1e6:.4f}".zfill(7)
    return " ".join([o["station"], "?", o["channel"], o["onset"], o["phase"][0].upper(), o["first_motion"],
                     t.strftime("%Y%m%d"), t.strftime("%H%M"), seconds, "QUAL", str(o["quality"]),
                     NO_VALUE, NO_VALUE, NO_VALUE]) + "\n"


def write_obs(observations, path):
    with open(path, "w") as f:
        f.write(OBS_HEADER)
        for o in observations:
            f.write(obs_line(o))


def read_obs(path):
    """The observations of an NLLOC_OBS file, as the JSON input carries them."""
    out = []
    with open(path) as fin:
        for line in fin:
            if line.startswith("#") or not line.strip():
                continue
            f = line.split()
            if f[9] != "QUAL":
                raise InputError(f"{path}: only QUAL error type is supported, got {f[9]}")
            t = dt.datetime.strptime(f[6] + f[7], "%Y%m%d%H%M") + dt.timedelta(seconds=float(f[8]))
            out.append({"station": f[0], "channel": f[2], "onset": f[3], "phase": f[4], "first_motion": f[5],
                        "time": time_to_iso(t), "quality": int(f[10])})
    return out


# ---------------------------------------------------------------------------
# NLLoc .hyp output
# ---------------------------------------------------------------------------

def _num(s):
    v = float(s)
    return int(v) if v.is_integer() and "." not in s and "e" not in s.lower() else v


def _pairs(fields):
    """`key value key value ...` tokens as a dict."""
    return {fields[i]: fields[i + 1] for i in range(0, len(fields) - 1, 2)}


def parse_hyp(path):
    """The blocks of a .grid0.loc.hyp, keyed by block name, plus the PHASE lines."""
    blocks, phases, in_phases = {}, [], False
    with open(path) as fin:
        lines = fin.readlines()
    for line in lines:
        f = line.split()
        if not f:
            continue
        if f[0] == "PHASE" and len(f) > 1 and f[1] == "ID":
            in_phases = True
            continue
        if f[0] == "END_PHASE":
            in_phases = False
            continue
        if in_phases:
            phases.append(f)
        elif f[0] == "NLLOC":
            m = re.match(r'NLLOC\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"', line)
            blocks["NLLOC"] = {"root": m.group(1), "status": m.group(2), "message": m.group(3)}
        elif f[0] in ("SIGNATURE", "COMMENT", "TRANSFORM"):
            blocks[f[0]] = line[len(f[0]):].strip().strip('"')
        else:
            blocks[f[0]] = f[1:]
    blocks["phases"] = phases
    return blocks


def _phase_time(f):
    t = dt.datetime.strptime(f[6] + f[7], "%Y%m%d%H%M") + dt.timedelta(seconds=float(f[8]))
    return time_to_iso(t)


def hyp_to_json(hyp):
    """The location as the output document describes it."""
    geo = hyp["GEOGRAPHIC"]
    ot = dt.datetime(*[int(v) for v in geo[1:6]]) + dt.timedelta(seconds=float(geo[6]))
    hypo = _pairs(hyp["HYPOCENTER"][:8])
    stat = _pairs(hyp["STATISTICS"])
    stat_geo = _pairs(hyp["STAT_GEOG"])
    qual = hyp["QUALITY"]
    oq = _pairs(hyp["QML_OriginQuality"])
    ou = _pairs(hyp["QML_OriginUncertainty"])
    ce = _pairs(hyp["QML_ConfidenceEllipsoid"])
    grid = hyp["GRID"]
    search = hyp["SEARCH"]
    vpvs = _pairs(hyp["VPVSRATIO"])
    m = re.search(r"NLLoc:(\S+)", hyp["SIGNATURE"])
    phases = []
    for f in hyp["phases"]:
        has_grid = float(f[18]) > -1e19
        phases.append({
            "station": f[0], "channel": f[2], "onset": f[3], "phase": f[4], "first_motion": f[5],
            "time": _phase_time(f), "error": float(f[10]),
            "travel_time": float(f[15]), "residual": float(f[16]), "weight": float(f[17]),
            "used": float(f[17]) > 0,
            "station_x": float(f[18]) if has_grid else None,
            "station_y": float(f[19]) if has_grid else None,
            "station_z": float(f[20]) if has_grid else None,
            "distance": float(f[21]), "azimuth": float(f[22]),
            "takeoff_azimuth": float(f[23]), "takeoff_dip": float(f[24]), "takeoff_quality": int(f[25]),
            "correction": float(f[26]),
        })
    return {
        "nll": {
            "version": m.group(1) if m else None,
            "status": hyp["NLLOC"]["status"], "message": hyp["NLLOC"]["message"],
            "transform": hyp["TRANSFORM"],
            "grid": dict(zip(("nx", "ny", "nz", "x0", "y0", "z0", "dx", "dy", "dz"), [_num(v) for v in grid[:9]])),
            "search": {"n_initial": int(search[2]), "n_evaluated": int(search[4]),
                       "smallest_node_side": [float(v) for v in search[6].split("/")],
                       "oct_tree_integral": float(search[8]), "scatter_volume": float(search[10])},
        },
        "origin": {
            "time": time_to_iso(ot), "latitude": float(geo[8]), "longitude": float(geo[10]), "depth": float(geo[12]),
            "x": float(hypo["x"]), "y": float(hypo["y"]), "z": float(hypo["z"]),
            "expectation": {"latitude": float(stat_geo["ExpectLat"]), "longitude": float(stat_geo["Long"]),
                            "depth": float(stat_geo["Depth"]),
                            "x": float(stat["ExpectX"]), "y": float(stat["Y"]), "z": float(stat["Z"])},
        },
        "quality": {
            "rms": float(qual[7]), "phases_used": int(qual[9]), "phases_associated": int(oq["assocPhCt"]),
            "stations_used": int(oq["usedStaCt"]), "gap": float(qual[11]), "secondary_gap": float(oq["secAzGap"]),
            "distance_min": float(oq["minDist"]), "distance_max": float(oq["maxDist"]),
            "distance_median": float(oq["medDist"]),
            "vp_vs_ratio": float(vpvs["VpVsRatio"]), "vp_vs_pairs": int(vpvs["Npair"]), "vp_vs_max_diff": float(vpvs["Diff"]),
            "pdf_max": float(qual[1]), "misfit_min": float(qual[3]), "misfit_max": float(qual[5]),
        },
        "uncertainty": {
            "covariance": {k.replace("Cov", "").lower(): float(stat[k]) for k in ("CovXX", "XY", "XZ", "YY", "YZ", "ZZ")},
            "ellipsoid": {"azimuth1": float(stat["EllAz1"]), "dip1": float(stat["Dip1"]), "length1": float(stat["Len1"]),
                          "azimuth2": float(stat["Az2"]), "dip2": float(stat["Dip2"]), "length2": float(stat["Len2"]),
                          "length3": float(stat["Len3"])},
            "horizontal": {"min": float(ou["minHorUnc"]), "max": float(ou["maxHorUnc"]), "azimuth": float(ou["azMaxHorUnc"])},
            "confidence_ellipsoid": {"semi_major": float(ce["semiMajorAxisLength"]), "semi_minor": float(ce["semiMinorAxisLength"]),
                                     "semi_intermediate": float(ce["semiIntermediateAxisLength"]),
                                     "plunge": float(ce["majorAxisPlunge"]), "azimuth": float(ce["majorAxisAzimuth"]),
                                     "rotation": float(ce["majorAxisRotation"])},
        },
        "phases": phases,
    }
