"""JSON I/O tests of yanll-locate, run inside the image (`make check`).

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
    """Control-file lines with the three LOCFILES paths and the INCLUDE path blanked."""
    out = []
    for line in text.splitlines():
        if line.startswith("LOCFILES"):
            f = line.split()
            out.append(f"LOCFILES <obs> {f[2]} <time> <out> {len(f)}")
        elif line.lstrip("#").startswith("INCLUDE"):
            out.append(line.split()[0] + " " + os.path.basename(line.split()[1]))
        else:
            out.append(line)
    return out


class ObservationFile(unittest.TestCase):
    def test_round_trip_matches_production_bytes(self):
        for run in runs():
            with self.subTest(run=run):
                obs = obs_of(run)
                doc = {"model": y.MODEL_3D, "dimension": "3d", "station_corrections": True,
                       "observations": y.read_obs(obs)}
                clean = y.validate_input(doc)
                text = y.OBS_HEADER + "".join(y.obs_line(o) for o in clean["observations"])
                with open(obs) as f:
                    self.assertEqual(text, f.read())


class InputFixtures(unittest.TestCase):
    def test_committed_inputs_are_what_obs2json_writes(self):
        for run in runs():
            for dim, model in (("1d", zone_of(run)), ("3d", y.MODEL_3D)):
                with self.subTest(run=run, dim=dim):
                    out = subprocess.run(["yanll-obs2json", "--model", model, "--dimension", dim, obs_of(run)],
                                         check=True, capture_output=True, text=True).stdout
                    with open(os.path.join(FIXTURES, run, f"input-{dim}.json")) as f:
                        self.assertEqual(json.loads(out), json.load(f))


class ControlFile(unittest.TestCase):
    def test_1d_matches_production(self):
        for run in runs():
            with self.subTest(run=run):
                prod = glob.glob(os.path.join(FIXTURES, run, "loc_1d", "*_loc.in"))[0]
                mine = y.control_1d(zone_of(run), "obs", "time", "out", True)
                with open(prod) as f:
                    self.assertEqual(normalized(mine), normalized(f.read()))

    def test_3d_matches_production(self):
        hdr = os.path.join(y.DATA, "model_3d", "model.P.mod.hdr")
        self.assertTrue(os.path.exists(hdr), f"{hdr} missing: the 3D model must be in the data directory")
        for run in runs():
            with self.subTest(run=run):
                prod = glob.glob(os.path.join(FIXTURES, run, "loc_3d", "*_loc.in"))[0]
                mine = y.control_3d("obs", "time", "out", True, hdr)
                with open(prod) as f:
                    self.assertEqual(normalized(mine), normalized(f.read()))

    def test_corrections_off_comments_the_include(self):
        self.assertIn("\n#INCLUDE ", y.control_1d(zone_of(EVENT), "obs", "time", "out", False))


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


class RejectsBadInput(unittest.TestCase):
    def locate(self, doc):
        return subprocess.run(["yanll-locate", "-"], input=json.dumps(doc), capture_output=True, text=True)

    def good(self):
        with open(os.path.join(FIXTURES, EVENT, "input-1d.json")) as f:
            return json.load(f)

    def test_unknown_key(self):
        doc = self.good()
        doc["starting_location"] = {"latitude": 43.2, "longitude": 13.4}
        r = self.locate(doc)
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown keys: starting_location", r.stderr)

    def test_quality_out_of_range(self):
        doc = self.good()
        doc["observations"][0]["quality"] = 5
        r = self.locate(doc)
        self.assertEqual(r.returncode, 2)
        self.assertIn("quality", r.stderr)

    def test_dimension_must_match_model(self):
        doc = self.good()
        doc["dimension"] = "3d"
        r = self.locate(doc)
        self.assertEqual(r.returncode, 2)
        self.assertIn("1d zone", r.stderr)

    def test_zone_without_corrections(self):
        doc = self.good()
        doc["model"] = "Sardegna_12"
        r = self.locate(doc)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no station corrections", r.stderr)


if __name__ == "__main__":
    unittest.main()
