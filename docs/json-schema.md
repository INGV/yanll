# JSON input and output

`yanll-locate` reads one JSON document with the parameters of a run and writes one JSON
document with the location. The tool is an adapter: from the input it writes the
`NLLOC_OBS` observation file and fills the NLLoc control-file template of the model
named in the input (`${YANLL_CONFIG}/models/<model>/locate.in`, see
`docs/configuration.md`), generates the travel-time grids the stations need, runs
`NLLoc` and maps the `.hyp` it writes to the output. With the INGV configuration
mounted the observation and control files are the production ones byte for byte.
`yanll-obs2json` turns an observation file into an input document;
`fixtures/events/<run>/input-{1d,3d}.json` were made with it.

```
docker compose run --rm -T yanll yanll-locate /fixtures/events/47442632_147825511/input-1d.json > out.json
docker compose run --rm -T yanll yanll-locate - < input.json > out.json
```

Exit codes: 0 located; 1 NLLoc ran but did not locate (`nll.status` is `REJECTED` or
`ABORTED` with NLLoc's message, or `NOT_LOCATED` with its warnings when it skipped the
event, for instance with fewer than 3 phases, and wrote no location: then the document
has no `origin`, `quality`, `uncertainty` or `phases`); 2 invalid input or incomplete
configuration (message on stderr, naming `docs/configuration.md` in the second case); 3
grid generation or NLLoc failure.

Conventions: times are ISO 8601 UTC with microseconds (`2026-10-04T20:12:29.160000Z`);
coordinates are decimal degrees, positive north and east; depths, distances and grid
coordinates are kilometres (depth positive down, `z` of a station is minus its
elevation); times and errors are seconds; angles are degrees. Unknown keys are
rejected.

## Input

```json
{
  "model": "Fascia-Adriatica_6a",
  "station_corrections": true,
  "event_id": "47442632",
  "origin_id": "147825511",
  "observations": [
    {"station": "MNTP", "channel": "HNZ", "onset": "?", "phase": "P", "first_motion": "D",
     "time": "2026-10-04T20:12:29.160000Z", "quality": 0},
    {"station": "MNTP", "channel": "HNZ", "onset": "?", "phase": "S", "first_motion": "?",
     "time": "2026-10-04T20:12:31.540000Z", "quality": 2}
  ]
}
```

| Key | Type | Meaning |
|---|---|---|
| `model` | string, required | the name of a model directory of the mounted configuration (`docs/configuration.md`): letters, digits, `_`, `-` and `.`. With `config/ingv/` a 1D zone nickname (`Alpi-Occidentali_1`, `Alpi-Centrali_2`, `Alpi-Orientali_3`, `Pianura-Padana_4`, `Fascia-Appenninica_5a`, `5b`, `5c`, `5d`, `Fascia-Adriatica_6a`, `6b`, `Gargano_7`, `Salento_8`, `Fascia-Tirrenica_9a`, `9b`, `Calabria_10`, `Sicilia_11`, `Sardegna_12`) or `TOMORAMA-2013`; the caller chooses the zone, as production picked it from the INGV epicentre with the polygons of `reference/production/opt/nll/zones_20211128/`. Whether a model is 1D or 3D is the model's business, not the input's |
| `station_corrections` | boolean, required | include the model's `corrections.in` (`LOCDELAY` lines; the production corrections, `CY`, in `config/ingv/`). A model without the file refuses `true` (`Sardegna_12`) |
| `event_id`, `origin_id` | string, optional, `[A-Za-z0-9-]+` | echoed to the output and used to name the NLLoc files (`<event_id>_<origin_id>`) |
| `observations` | array, required, non-empty | one object per arrival, in the order they are written to the observation file |

Each observation:

| Key | Type | Meaning |
|---|---|---|
| `station` | string, required | station code, 1 to 6 alphanumeric characters; the only key NLLoc uses to find the travel-time grid and the correction (network, location and channel play no part, as in production) |
| `phase` | string, required | phase label; only its first letter, upper-cased, is written (`Pg` → `P`, `Sn` → `S`), as `02_qml_parser.py` does |
| `time` | string, required | pick time, ISO 8601 with a UTC designator |
| `quality` | integer 0 to 9, required | pick class, mapped to seconds by the `LOCQUAL2ERR` line of the model's template (`0.05 0.2 0.45 0.8 99999.9` in `config/ingv/`: class 4 and above get the last value, so weight 0). Production derives it from the QuakeML pick uncertainty: 0.1 s → 0, 0.3 → 1, 0.6 → 2, 1.0 → 3, 3.0 → 4, 10.0 → 8 |
| `channel` | string, optional | channel code, echoed (`?` when absent) |
| `onset` | `"?"`, `"i"`, `"e"`, `"impulsive"` or `"emergent"`, optional | onset, echoed (`?` when absent; production writes the QuakeML word) |
| `first_motion` | `"?"`, `"U"` or `"D"`, optional | first motion, echoed (`?` when absent) |

There is no starting location: NLLoc searches the whole grid of the model, and
production never used the INGV epicentre for anything but the choice of the zone.

## Output

The values below are those of the production run of the fixture event `47442632_147825511`, except
`nll.version`, which is the container's; the container reproduces them within the
project tolerance (1 km in epicentre, 2 km in depth, 0.5 s in origin time), not to the
digit.

```json
{
  "model": "Fascia-Adriatica_6a",
  "station_corrections": true,
  "event_id": "47442632",
  "origin_id": "147825511",
  "nll": {
    "version": "v7.1.05(18Apr2025)",
    "status": "LOCATED",
    "message": "Location completed.",
    "transform": "SIMPLE LatOrig 43.500000  LongOrig 13.600000  RotCW 0.000000",
    "grid": {"nx": 561, "ny": 721, "nz": 225, "x0": -140, "y0": -180, "z0": -3, "dx": 0.5, "dy": 0.5, "dz": 0.5},
    "search": {"n_initial": 4000, "n_evaluated": 20000, "smallest_node_side": [0.109375, 0.140625, 0.087891],
               "oct_tree_integral": 20.4423, "scatter_volume": 20.4423},
    "control_file": "CONTROL 2 123456 ...\nTRANS SIMPLE 43.500000 13.600000 0.0\n..."
  },
  "origin": {
    "time": "2026-10-04T20:12:26.171713Z", "latitude": 43.189289, "longitude": 13.425158, "depth": 16.379883,
    "x": -14.1641, "y": -34.5234, "z": 16.3799,
    "expectation": {"latitude": 43.189041, "longitude": 13.423279, "depth": 16.063216,
                    "x": -14.3163, "y": -34.551, "z": 16.0632}
  },
  "quality": {
    "rms": 0.308913, "phases_used": 39, "phases_associated": 85, "stations_used": 22,
    "gap": 57.8591, "secondary_gap": 91.3182,
    "distance_min": 6.77941, "distance_max": 54.9387, "distance_median": 35.0226,
    "vp_vs_ratio": 1.83103, "vp_vs_pairs": 24, "vp_vs_max_diff": 11.42,
    "pdf_max": 6.33806e+114, "misfit_min": 34.0, "misfit_max": 36.4395
  },
  "uncertainty": {
    "covariance": {"xx": 1.03091, "xy": -0.150733, "xz": 0.998602, "yy": 0.80054, "yz": -0.516006, "zz": 3.26502},
    "ellipsoid": {"azimuth1": 121.187, "dip1": -23.0244, "length1": 1.48663,
                  "azimuth2": 30.5759, "dip2": -1.43768, "length2": 1.60145, "length3": 3.635364},
    "horizontal": {"min": 1.29223, "max": 1.59452, "azimuth": 116.307},
    "confidence_ellipsoid": {"semi_major": 3.63536, "semi_minor": 1.48663, "semi_intermediate": 1.60145,
                             "plunge": 66.9255, "azimuth": 117.199, "rotation": 87.4554}
  },
  "phases": [
    {"station": "MNTP", "channel": "HNZ", "onset": "?", "phase": "P", "first_motion": "D",
     "time": "2026-10-04T20:12:29.160000Z", "error": 0.05,
     "travel_time": 2.8929, "residual": 0.0781, "weight": 1.4762, "used": true,
     "station_x": -10.6012, "station_y": -40.2911, "station_z": -0.325,
     "distance": 6.7794, "azimuth": 148.29,
     "takeoff_azimuth": 359.0, "takeoff_dip": -1.0, "takeoff_quality": 0, "correction": 0.0173}
  ]
}
```

| Key | From the `.hyp` | Meaning |
|---|---|---|
| `model`, `station_corrections`, `event_id`, `origin_id` | input | echoed |
| `nll.version` | `SIGNATURE` | the NLLoc that ran |
| `nll.status`, `nll.message` | `NLLOC` | `LOCATED`, `REJECTED` or `ABORTED` and NLLoc's explanation |
| `nll.transform` | `TRANSFORM` | the projection of the grid coordinates (`x`, `y` below) |
| `nll.grid` | `GRID` | the location grid: nodes, origin and spacing in km |
| `nll.search` | `SEARCH` | octree statistics: nodes initially and in all evaluated, smallest node side (x, y, z), PDF integral and scatter volume |
| `nll.control_file` | | the control file the tool wrote (the model's template with the placeholders filled), for traceability |
| `origin.time`, `latitude`, `longitude`, `depth` | `GEOGRAPHIC` | the maximum-likelihood hypocentre |
| `origin.x`, `y`, `z` | `HYPOCENTER` | the same in grid coordinates |
| `origin.expectation` | `STAT_GEOG`, `STATISTICS` | the expectation of the PDF, geographic and grid |
| `quality.rms`, `phases_used`, `gap` | `QUALITY` | residual RMS, phases with weight > 0, azimuthal gap |
| `quality.phases_associated`, `stations_used`, `secondary_gap`, `distance_*` | `QML_OriginQuality` | arrivals read, stations with weight > 0, secondary gap, min, max and median epicentral distance of the used stations |
| `quality.vp_vs_*` | `VPVSRATIO` | Vp/Vs estimate from the S-P pairs, number of pairs, max S-P difference |
| `quality.pdf_max`, `misfit_min`, `misfit_max` | `QUALITY` | `Pmax`, `MFmin`, `MFmax` |
| `uncertainty.covariance` | `STATISTICS` | covariance of the PDF scatter, km² |
| `uncertainty.ellipsoid` | `STATISTICS` | 68 % error ellipsoid: azimuth, dip and length of the two minor axes, length of the major axis |
| `uncertainty.horizontal` | `QML_OriginUncertainty` | horizontal uncertainty: min and max semi-axis and the azimuth of the max |
| `uncertainty.confidence_ellipsoid` | `QML_ConfidenceEllipsoid` | the same ellipsoid in QuakeML terms |
| `phases[]` | `PHASE` lines | one per arrival, in NLLoc's order (by distance): the input fields as written, then `error` (seconds, from the quality class), `travel_time` predicted, `residual`, `weight` (0 means unused, `used` says so), the station in grid coordinates (`null` when the station has no travel-time grid), epicentral `distance` and `azimuth`, take-off `takeoff_*` (placeholders `359.0`, `-1.0`, `0` when the templates say `ANGLES_NO`, as the INGV ones do: production never read angle grids) and the station `correction` applied |
