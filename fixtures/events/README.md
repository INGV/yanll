# Comparison events

Production runs copied from `nll.int.ingv.it` on 2026-10-15, one directory per
`<eventid>_<originid>` run, taken from the runs of the previous 30 days. Each directory
holds the observation file (`obs/`, identical for the 1D and the 3D run), the 1D run
(`loc_1d/`) and the 3D run (`loc_3d/`) as left in `/opt/nll/loc_{1d,3d}/Done/`, without
the binary `.scat` scatter files and the `last.*` duplicates. These files are oracles:
never edit them.

Selection: one event per zone that had events with at least 10 phases in the period
(16 of the 17 zones; `Sardegna_12` had none), preferring many used phases and a small
gap, plus four more from the busiest zones, 20 in all. The 21st,
`46761811_147805861`, is a 109 km deep Tyrrhenian event located at the bottom edge of the
1D grid (the grid stops at 109 km) and 150 km deep in 3D: it is kept as a stress case and
reported separately, not counted in the acceptance.

The column `nogrid3d` lists the stations that had no 3D travel-time grid in production
(their phases enter the 3D location with weight 0, see `docs/production-flow.md`,
section 6); `nphs` is the number of phases NLLoc used.

| run | zone | origin time (1D) | lat 1D | lon 1D | depth 1D | nphs 1D | lat 3D | lon 3D | depth 3D | nphs 3D | nogrid3d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 46762511_147809831 | Sicilia_11 | 2026-10-04T02:06:57.366 | 38.387566 | 14.587107 | 6.096680 | 34 | 38.383229 | 14.598240 | 8.003418 | 28 | ISNA,IVLO,SALIN |
| 47179932_147525951 | Fascia-Adriatica_6b | 2026-09-16T16:38:56.144 | 41.398727 | 15.223837 | 9.216797 | 28 | 41.420535 | 15.192631 | 12.017676 | 28 |  |
| 47181372_147529981 | Fascia-Appenninica_5b | 2026-09-17T00:46:55.674 | 43.082576 | 13.033264 | 12.095215 | 83 | 43.086531 | 13.031143 | 15.490796 | 83 |  |
| 47181522_147530211 | Gargano_7 | 2026-09-17T01:28:57.079 | 41.731582 | 15.778133 | 21.125977 | 35 | 41.730212 | 15.755700 | 22.978174 | 35 |  |
| 47181612_147530621 | Fascia-Appenninica_5b | 2026-09-17T02:14:04.345 | 43.082576 | 13.034997 | 12.007324 | 66 | 43.088554 | 13.033568 | 15.215308 | 66 |  |
| 47189672_147547431 | Sicilia_11 | 2026-09-17T19:46:04.186 | 38.037305 | 15.444682 | 24.685547 | 32 | 38.068210 | 15.455354 | 21.049756 | 21 | BASIC,CNDF,EPMN,GIOM,LAZR,MLPS,RICA |
| 47190522_147550641 | Fascia-Tirrenica_9b | 2026-09-18T03:40:19.948 | 41.514845 | 13.076128 | 3.591797 | 27 | 41.511209 | 13.078268 | 10.049902 | 22 | AMSN,FEN,ITR,VERO |
| 47199202_147568901 | Fascia-Appenninica_5d | 2026-09-19T00:54:59.378 | 40.620687 | 15.537820 | 12.161133 | 29 | 40.626001 | 15.547168 | 15.618701 | 29 | CARP |
| 47199392_147569191 | Alpi-Occidentali_1 | 2026-09-19T02:43:17.034 | 44.617003 | 7.207094 | 10.579102 | 27 | 44.615915 | 7.230127 | 12.883496 | 17 | CRI,CUN,ENAUX,FENE,SLZ,VIND |
| 47209832_147595821 | Fascia-Appenninica_5c | 2026-09-20T11:21:38.406 | 41.965223 | 14.002409 | 12.688477 | 33 | 41.971111 | 14.015913 | 16.681299 | 33 | H20J |
| 47227992_147642011 | Alpi-Occidentali_1 | 2026-09-23T07:49:47.185 | 44.615034 | 7.211061 | 9.700195 | 33 | 44.616787 | 7.230010 | 13.040918 | 20 | CRI,CUN,ENAUX,FENE,ORIF,SLZ,VIND |
| 47239632_147670961 | Pianura-Padana_4 | 2026-09-24T23:50:13.238 | 44.413594 | 12.218227 | 14.050781 | 26 | 44.419377 | 12.274412 | 33.938672 | 26 |  |
| 47244052_147679951 | Fascia-Appenninica_5b | 2026-09-25T13:15:22.248 | 43.709465 | 11.889478 | 1.965820 | 55 | 43.711021 | 11.881832 | 7.826318 | 53 | VMGN |
| 47258752_147716281 | Fascia-Tirrenica_9a | 2026-09-27T14:31:11.951 | 43.240156 | 11.416827 | 4.998047 | 32 | 43.245919 | 11.429104 | 6.035645 | 16 | LOCA,MALA0,MALA1,MALA2,MALA3,MALA4,MALA5,MNT |
| 47425052_147749401 | Alpi-Orientali_3 | 2026-09-30T02:58:53.891 | 46.280373 | 12.962747 | 3.921387 | 33 | 46.281990 | 12.964507 | 7.285181 | 33 |  |
| 47442632_147825511 | Fascia-Adriatica_6a | 2026-10-04T20:12:26.172 | 43.189289 | 13.425158 | 16.379883 | 39 | 43.200465 | 13.431226 | 16.523877 | 35 | AMAD,AMEN,MRSC |
| 47443552_147830771 | Fascia-Appenninica_5a | 2026-10-05T02:04:06.058 | 44.567187 | 10.462496 | 9.568359 | 58 | 44.563035 | 10.445750 | 12.962207 | 51 | BRR,FELT,FRN,LNG,PDN14,VMGN,WTTA |
| 47457632_147860561 | Salento_8 | 2026-10-06T16:22:10.454 | 40.746797 | 16.455193 | 12.205078 | 11 | 40.762827 | 16.453449 | 14.497070 | 11 |  |
| 47501792_147956961 | Calabria_10 | 2026-10-10T06:29:43.859 | 38.408363 | 15.818951 | 8.469727 | 48 | 38.406148 | 15.822274 | 20.321680 | 19 | ARMO,BASIC,BRICA,CHCE,CIMI,CO22,CSGE1,DLNV,FALC,GIOM,MFG,MUGA,NICCA,RCPC,RICA,SAAM,SPDC,UC01,VBL2 |
| 47512672_147986391 | Alpi-Centrali_2 | 2026-10-12T02:07:37.553 | 45.647879 | 10.690722 | 4.250977 | 37 | 45.626701 | 10.687594 | 9.990869 | 34 | PDN14,SAL |
