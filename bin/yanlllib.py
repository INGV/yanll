"""Shared code of yanll-locate and yanll-obs2json.

Reproduces, from JSON, what the production scripts build from a QuakeML: the NLLOC_OBS
observation file (02_qml_parser.py) and the NLLoc control file (04_locator_nll_1d.sh,
04_locator_nll_3d.sh), byte for byte, and reads the .hyp NLLoc writes back into JSON.
"""
import datetime as dt
import json
import os
import re

MODEL_3D = "TOMORAMA-2013"
MODELS_1D_DIR = "/opt/yanll/models_1d"
CORRECTIONS_1D = MODELS_1D_DIR + "/correzioni/correzioni_{zone}.in"
CORRECTIONS_3D = "/opt/yanll/corrections_3d/corrections_TOMORAMA-2013.in"
DATA = os.environ.get("YANLL_DATA", "/data")

OBS_HEADER = ("#Station_name Instrument Component P_phase_onset Phase_descriptor First_motion "
              "Date Hour_minute Seconds Err_type Err Err_mag Coda_duration Amplitude\n")
# The production heredocs pad this line with 48 blanks.
CONTROL_LINE = "CONTROL 2 123456" + " " * 48
NO_VALUE = "-1.00E+00"

INPUT_KEYS = {"model", "dimension", "station_corrections", "observations", "event_id", "origin_id"}
OBSERVATION_KEYS = {"station", "channel", "onset", "phase", "first_motion", "time", "quality"}


class InputError(Exception):
    """The input document is not a valid run: reported to the caller, exit code 2."""


def zones():
    """The 1D zones shipped in the image, from their model files."""
    return sorted(f[len("model_"):-len(".in")] for f in os.listdir(MODELS_1D_DIR)
                  if f.startswith("model_") and f.endswith(".in"))


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
    for key in ("model", "dimension", "station_corrections", "observations"):
        if key not in doc:
            raise InputError(f"missing key: {key}")
    model, dim = doc["model"], doc["dimension"]
    if model == MODEL_3D:
        if dim != "3d":
            raise InputError(f"model {MODEL_3D} is 3d, dimension is {dim!r}")
    elif model in zones():
        if dim != "1d":
            raise InputError(f"model {model} is a 1d zone, dimension is {dim!r}")
    else:
        raise InputError(f"unknown model {model!r}: one of {', '.join(zones())}, {MODEL_3D}")
    if not isinstance(doc["station_corrections"], bool):
        raise InputError("station_corrections must be true or false")
    if doc["station_corrections"] and dim == "1d" and not os.path.exists(CORRECTIONS_1D.format(zone=model)):
        raise InputError(f"no station corrections exist for zone {model}: set station_corrections to false")
    for key in ("event_id", "origin_id"):
        if key in doc and not re.fullmatch(r"[A-Za-z0-9-]+", str(doc[key])):
            raise InputError(f"{key} must be alphanumeric")
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
        if not isinstance(o["quality"], int) or isinstance(o["quality"], bool) or not 0 <= o["quality"] <= 4:
            raise InputError(f"observation {i}: quality must be an integer from 0 to 4")
        for key, allowed in (("onset", {"?", "i", "e"}), ("first_motion", {"?", "U", "D"})):
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
# NLLOC_OBS observation file (02_qml_parser.py)
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
    """The observations of a production NLLOC_OBS file, as the JSON input carries them."""
    out = []
    for line in open(path):
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
# NLLoc control file (04_locator_nll_1d.sh, 04_locator_nll_3d.sh)
# ---------------------------------------------------------------------------

def awk_num(x):
    """A number the way awk prints it: no decimals when integral, else %.6g."""
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:.6g}"


def zone_centre(zone):
    """lat0, lon0 and the half extents (km) of the location grid from centri_20211027.lst."""
    for line in open(os.path.join(MODELS_1D_DIR, "centri_20211027.lst")):
        f = line.split()
        if len(f) > 11 and f"{f[4]}_{f[2]}" == zone:
            return float(f[11]), float(f[10]), float(f[8]), float(f[9])
    raise InputError(f"zone {zone} not in centri_20211027.lst")


def model_min_depth(zone):
    for line in open(os.path.join(MODELS_1D_DIR, f"model_{zone}.in")):
        if not line.startswith("#"):
            return float(line.split()[1])


def locgrid_1d(zone):
    """The LOCGRID of 04_locator_nll_1d.sh: model step x5, extent from the zone table,
    two nodes dropped at the top and bottom, origin so that the grid is centred."""
    _, _, half_x, half_y = zone_centre(zone)
    model_nz, model_step, mul = 1141, 0.1, 5.0
    step = model_step * mul
    nx = (half_x * 2) / step + 1
    ny = (half_y * 2) / step + 1
    nz = ((model_nz - 1) * model_step) / step + 1 - 4
    x0 = (nx - 1) * step / -2
    y0 = (ny - 1) * step / -2
    z0 = model_min_depth(zone) + step * 2
    z0 = 0 if z0 > 0 else z0
    return " ".join(awk_num(v) for v in (nx, ny, nz, x0, y0, z0, step, step, step))


COMMON_TAIL = [
    "LOCPHASEID  P   P p G PN Pn PG Pg",
    "LOCPHASEID  S   S s G SN Sn SG Sg",
    "LOCQUAL2ERR 0.05 0.2 0.45 0.8 99999.9",
]


def control_1d(zone, obs_path, time_root, out_root, corrections):
    lat0, lon0, _, _ = zone_centre(zone)
    include = ("" if corrections else "#") + "INCLUDE " + CORRECTIONS_1D.format(zone=zone)
    lines = [
        CONTROL_LINE,
        f"TRANS SIMPLE {lat0:.6f} {lon0:.6f} 0.0",
        "LOCSIG INGV - Istituto Nazionale di Geofisica e Vulcanologia",
        "LOCCOM INGV-1D (NonLinLoc Location)",
        f"LOCFILES {obs_path} NLLOC_OBS {time_root}  {out_root}",
        "LOCHYPOUT  SAVE_NLLOC_ALL",
        "LOCSEARCH  OCT 20 20 10 0.02 20000 5000 0 1",
        "#LOCSEARCH  OCT 20 20 10 0.02 20000 5000 0 1",
        f"LOCGRID  {locgrid_1d(zone)}  PROB_DENSITY  SAVE",
        "LOCMETH EDT_OT_WT 9999.0 3 -1 -1 -1 -1 -1. 1",
        "LOCGAU 0.2 0.0",
        "LOCGAU2 0.05 0.1 5.0",
    ] + COMMON_TAIL + [include]
    return "\n".join(lines) + "\n"


def control_3d(obs_path, time_root, out_root, corrections, model_hdr):
    # The grid is the whole model grid as its header states it, with Z0 forced to -4.
    f = open(model_hdr).readline().split()
    grid = " ".join(f[0:5] + ["-4"] + f[6:9])
    include = ("" if corrections else "#") + "INCLUDE " + CORRECTIONS_3D
    lines = [
        CONTROL_LINE,
        "TRANS  TRANS_MERC WGS-84  0.0 15.0  0.0",
        "LOCSIG INGV - Istituto Nazionale di Geofisica e Vulcanologia",
        "LOCCOM INGV-3d (NonLinLoc Location)",
        f"LOCFILES {obs_path} NLLOC_OBS {time_root}  {out_root}",
        "LOCHYPOUT  SAVE_NLLOC_ALL",
        "#LOCHYPOUT SAVE_NLLOC_ALL NLL_FORMAT_VER_2 # Valutare l'uso del formato 2",
        "LOCSEARCH OCT 24 24 20 0.01 50000 5000 0 1",
        f"LOCGRID  {grid}  PROB_DENSITY  SAVE",
        "LOCMETH EDT_OT_WT 9999.0 3 150 0 -1.80 300 -1 1",
        "LOCGAU 0.2 0.0",
        "LOCGAU2 0.01 0.05 2.0 # 3D",
    ] + COMMON_TAIL + [include]
    return "\n".join(lines) + "\n"


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
    for line in open(path):
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
