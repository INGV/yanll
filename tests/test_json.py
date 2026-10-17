"""JSON I/O tests of yanll-locate, run in the container with the INGV configuration
mounted at /config and this directory at /tests:

    docker compose run --rm yanll python3 -m unittest discover -s /tests -v

They use the production fixtures mounted at /fixtures/events as oracles: the
observation file and the control file the tool writes must be the production ones byte
for byte (paths aside), the committed input documents must be what yanll-obs2json
produces, and one 1D location must reproduce production within the project tolerance.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, "/opt/yanll/bin")
import yanlllib as y  # noqa: E402

FIXTURES = os.environ.get("YANLL_FIXTURES", "/fixtures/events")
MODEL_3D = "TOMORAMA-2013"
EVENT = "47442632_147825511"
TOL_EPI_KM, TOL_DEP_KM, TOL_OT_S = 1.0, 2.0, 0.5


def runs():
    return sorted(os.path.basename(d) for d in glob.glob(os.path.join(FIXTURES, "*")) if os.path.isdir(d))


def obs_of(run):
    return glob.glob(os.path.join(FIXTURES, run, "obs", "*.phsnll"))[0]


def zone_of(run):
    name = glob.glob(os.path.join(FIXTURES, run, "loc_1d", "*_nlloc1D_*_loc.in"))[0]
    return name.split("_nlloc1D_")[1][:-len("_loc.in")]


def normalized(text):
    """Control-file lines with the three LOCFILES paths blanked and the INCLUDE path
    dropped (production names the file correzioni_<zone>.in, the configuration
    corrections.in; the comment mark that disables it is kept)."""
    out = []
    for line in text.splitlines():
        if line.startswith("LOCFILES"):
            f = line.split()
            out.append(f"LOCFILES <obs> {f[2]} <time> <out> {len(f)}")
        elif line.lstrip("#").startswith("INCLUDE"):
            out.append(line.split()[0])
        else:
            out.append(line)
    return out


class ObservationFile(unittest.TestCase):
    def test_round_trip_matches_production_bytes(self):
        for run in runs():
            with self.subTest(run=run):
                obs = obs_of(run)
                doc = {"model": MODEL_3D, "station_corrections": True, "observations": y.read_obs(obs)}
                clean = y.validate_input(doc)
                text = y.OBS_HEADER + "".join(y.obs_line(o) for o in clean["observations"])
                with open(obs) as f:
                    self.assertEqual(text, f.read())


class InputFixtures(unittest.TestCase):
    def test_committed_inputs_are_what_obs2json_writes(self):
        for run in runs():
            for dim, model in (("1d", zone_of(run)), ("3d", MODEL_3D)):
                with self.subTest(run=run, dim=dim):
                    out = subprocess.run(["yanll-obs2json", "--model", model, obs_of(run)],
                                         check=True, capture_output=True, text=True).stdout
                    with open(os.path.join(FIXTURES, run, f"input-{dim}.json")) as f:
                        self.assertEqual(json.loads(out), json.load(f))


class ControlFile(unittest.TestCase):
    def test_1d_matches_production(self):
        for run in runs():
            with self.subTest(run=run):
                prod = glob.glob(os.path.join(FIXTURES, run, "loc_1d", "*_loc.in"))[0]
                mine = y.locate_control(zone_of(run), "obs", "time", "out", True)
                with open(prod) as f:
                    self.assertEqual(normalized(mine), normalized(f.read()))

    def test_3d_matches_production(self):
        for run in runs():
            with self.subTest(run=run):
                prod = glob.glob(os.path.join(FIXTURES, run, "loc_3d", "*_loc.in"))[0]
                mine = y.locate_control(MODEL_3D, "obs", "time", "out", True)
                with open(prod) as f:
                    self.assertEqual(normalized(mine), normalized(f.read()))

    def test_corrections_off_comments_the_include(self):
        self.assertIn("\n#INCLUDE ", y.locate_control(zone_of(EVENT), "obs", "time", "out", False))


class HypMapping(unittest.TestCase):
    def test_production_hyp_values(self):
        """The mapping against literal values of the production .hyp of the event."""
        prod_hyp = [h for h in glob.glob(os.path.join(FIXTURES, EVENT, "loc_1d", "*.grid0.loc.hyp")) if ".sum." not in h][0]
        prod = y.hyp_to_json(y.parse_hyp(prod_hyp))
        self.assertEqual(prod["nll"]["version"], "v7.00.00(27Oct2017)")
        self.assertEqual(prod["origin"]["time"], "2026-10-04T20:12:26.171713Z")
        self.assertEqual((prod["origin"]["latitude"], prod["origin"]["longitude"], prod["origin"]["depth"]),
                         (43.189289, 13.425158, 16.379883))
        self.assertEqual((prod["quality"]["rms"], prod["quality"]["phases_used"], prod["quality"]["gap"]),
                         (0.308913, 39, 57.8591))
        self.assertEqual(prod["uncertainty"]["ellipsoid"]["length3"], 3.635364)
        mntp = [p for p in prod["phases"] if p["station"] == "MNTP" and p["phase"] == "P"][0]
        self.assertEqual((mntp["travel_time"], mntp["residual"], mntp["weight"], mntp["distance"], mntp["correction"]),
                         (2.8929, 0.0781, 1.4762, 6.7794, 0.0173))
        self.assertEqual((mntp["station_x"], mntp["station_y"], mntp["station_z"]), (-10.6012, -40.2911, -0.325))
        prod3 = y.hyp_to_json(y.parse_hyp([h for h in glob.glob(os.path.join(FIXTURES, EVENT, "loc_3d", "*.grid0.loc.hyp")) if ".sum." not in h][0]))
        amad = [p for p in prod3["phases"] if p["station"] == "AMAD"][0]
        self.assertFalse(amad["used"])
        self.assertIsNone(amad["station_x"])


class Locate1D(unittest.TestCase):
    def test_reproduces_production_within_tolerance(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.json")
            r = subprocess.run(["yanll-locate", "-o", out, os.path.join(FIXTURES, EVENT, "input-1d.json")],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out) as f:
                result = json.load(f)
        prod_hyp = [h for h in glob.glob(os.path.join(FIXTURES, EVENT, "loc_1d", "*.grid0.loc.hyp")) if ".sum." not in h][0]
        prod = y.hyp_to_json(y.parse_hyp(prod_hyp))
        self.assertEqual(result["nll"]["status"], "LOCATED")
        self.assertEqual(result["model"], zone_of(EVENT))
        self.assertEqual(len(result["phases"]), len(prod["phases"]))
        self.assertEqual(result["quality"]["phases_used"], prod["quality"]["phases_used"])
        d_lat = (result["origin"]["latitude"] - prod["origin"]["latitude"]) * 111.2
        d_lon = (result["origin"]["longitude"] - prod["origin"]["longitude"]) * 111.2 * 0.73
        self.assertLessEqual((d_lat ** 2 + d_lon ** 2) ** 0.5, TOL_EPI_KM)
        self.assertLessEqual(abs(result["origin"]["depth"] - prod["origin"]["depth"]), TOL_DEP_KM)
        t_res, t_prod = (y.parse_time(doc["origin"]["time"]) for doc in (result, prod))
        self.assertLessEqual(abs((t_res - t_prod).total_seconds()), TOL_OT_S)
        self.assertIn("LOCGRID  561 721 225 -140 -180 -3 0.5 0.5 0.5", result["nll"]["control_file"])


def locate(doc, env=None):
    return subprocess.run(["yanll-locate", "-"], input=json.dumps(doc), capture_output=True, text=True, env=env)


def good_input():
    with open(os.path.join(FIXTURES, EVENT, "input-1d.json")) as f:
        return json.load(f)


class LocateEdgeCases(unittest.TestCase):
    def test_too_few_phases_is_reported_not_failed(self):
        doc = good_input()
        doc["observations"] = doc["observations"][:2]
        r = locate(doc)
        self.assertEqual(r.returncode, 1, r.stderr)
        result = json.loads(r.stdout)
        self.assertEqual(result["nll"]["status"], "NOT_LOCATED")
        self.assertIn("too few observations", result["nll"]["message"])

    def test_station_missing_from_catalog_gets_weight_zero(self):
        doc = good_input()
        doc["observations"].append({"station": "ZZZZ", "phase": "P", "time": "2026-10-04T20:12:33.000000Z", "quality": 0})
        r = locate(doc)
        self.assertEqual(r.returncode, 0, r.stderr)
        zzzz = [p for p in json.loads(r.stdout)["phases"] if p["station"] == "ZZZZ"][0]
        self.assertFalse(zzzz["used"])
        self.assertIsNone(zzzz["station_x"])


class Configuration(unittest.TestCase):
    """Without a configuration every tool stops and names the documentation."""

    def test_locate_without_configuration(self):
        with tempfile.TemporaryDirectory() as empty:
            r = locate(good_input(), env={**os.environ, "YANLL_CONFIG": empty})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("docs/configuration.md", r.stderr)

    def test_make_grids_without_configuration(self):
        with tempfile.TemporaryDirectory() as empty:
            r = subprocess.run(["yanll-make-grids", zone_of(EVENT), "MNTP"], capture_output=True, text=True,
                               env={**os.environ, "YANLL_CONFIG": empty})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("docs/configuration.md", r.stderr)


class RejectsBadInput(unittest.TestCase):
    def test_unknown_key(self):
        doc = good_input()
        doc["starting_location"] = {"latitude": 43.2, "longitude": 13.4}
        r = locate(doc)
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown keys: starting_location", r.stderr)

    def test_quality_out_of_range(self):
        doc = good_input()
        doc["observations"][0]["quality"] = 10
        r = locate(doc)
        self.assertEqual(r.returncode, 2)
        self.assertIn("quality", r.stderr)

    def test_unknown_model(self):
        doc = good_input()
        doc["model"] = "Nowhere_99"
        r = locate(doc)
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown model", r.stderr)

    def test_model_without_corrections(self):
        doc = good_input()
        doc["model"] = "Sardegna_12"
        r = locate(doc)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no station corrections", r.stderr)


if __name__ == "__main__":
    unittest.main()
