# Tracking documentation index

Auto-generated index of files and per-directory READMEs.

## How to regenerate

```bash
python3 scripts/autoreadme.py --root . --write
```

## Directories

- `./README.md`
- `components/README.md`
- `components/backup/README.md`
- `include/README.md`
- `src/README.md`
- `test/README.md`
- `test/testTrackFinder/README.md`
- `test/testTrackFinder/Archive/README.md`
- `test/testTrackFinder/params/README.md`
- `test/testTrackFinder/scripts/README.md`
- `test/testTracksFromGenParticles/README.md`

## All files

| Path | Summary | Doc | Tags |
|---|---|---|---|
| `CMakeLists.txt` | Tracking/CMakeLists.txt | no |  |
| `components/backup/GenFit2DCHFitter.txt` | ====================================================================== | no |  |
| `components/backup/GGTF_Tracking.txt` | ====================================================================== | no |  |
| `components/backup/GGTF_Tracking__12_3_25.txt` | ====================================================================== | no |  |
| `components/backup/SimpleFitDCHFitter.txt` | ====================================================================== | no |  |
| `components/backup/ThreePointFitter.txt` | ====================================================================== | no |  |
| `components/DCHLooperEventFilter.cpp` | include "GaudiKernel/Algorithm.h" | no |  |
| `components/fit_ggtf_tracks.cpp` | fit_ggtf_tracks.cpp — Podio Frames (ROOTReader) backend | no |  |
| `components/GenFit2DCHFitter.cpp` | Gaudi/k4FWCore Transformer that fits IDEA drift-chamber GGTF track candidates using GenFit2 wire measurements (WireMeasurementNew), producing physics-clean EDM4hep TrackStates at the IP with robust publish-state selection, observability gating, optional TGeo material effects, and per-event robust pT summary metadata. | yes | DAF, FCCee, Gaudi, GenFit2, IDEA, Kalman, TGeo, WireMeasurementNew, drift-chamber, k4FWCore, key4hep, material-effects, metadata, pT-resolution, robust-stats, tracking |
| `components/GGTF_tracking.cpp` | ====================================================================== | no |  |
| `components/PlotTrackHitResiduals.cpp` | Gaudi | no |  |
| `components/SimpleFitDCHFitter.cpp` | ====================================================================== | no |  |
| `components/ThreePointFitter.cpp` | ====================================================================== | no |  |
| `components/TrackdNdxDelphesBased.cpp` | include "TrackdNdxDelphesBased.h" | no |  |
| `components/TrackdNdxDelphesBased.h` | pragma once | no |  |
| `components/TracksFromGenParticles.cpp` | include "Gaudi/Property.h" | no |  |
| `config_Tracking.yaml` |  | no |  |
| `include/GenFitter.h` | pragma once | no |  |
| `include/utils.hpp` | ifndef UTILS_HPP | no |  |
| `src/GenFitter.cpp` | include "GenFitter.h" | no |  |
| `src/utils.cpp` | include "utils.hpp" | no |  |
| `test/runGenFitTrackingOnSimplifiedDriftChamber.py` | ################# Particle gun setup | no |  |
| `test/testTrackFinder/.__afs724E` |  | no |  |
| `test/testTrackFinder/Archive/compare_pt_trackstate_vs_hitcircle.py` | compare_pt_trackstate_vs_hitcircle.py | no |  |
| `test/testTrackFinder/Archive/ddsim_local.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/Archive/filetest.sh` | PODIO “split” layout usually has: | no |  |
| `test/testTrackFinder/Archive/generate_joblist.py` |  | no |  |
| `test/testTrackFinder/Archive/local_chain_all.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/Archive/make_ptres.py` | !/usr/bin/env python3 | no |  |
| `test/testTrackFinder/Archive/make_sigma_pt_plot.py` | Try binding ROOT TTreeReaderValue('vector<type>') for the given branch. | no |  |
| `test/testTrackFinder/Archive/pt_resolution_plot_pyroot.py` | Pick best index given optional std::vector<int> (or float/bool) branches. | no |  |
| `test/testTrackFinder/Archive/ptres_from_edm4hep.py` | Returns (eta, E_GeV or None, pt_GeV or None) parsed from the path. | no |  |
| `test/testTrackFinder/Archive/reco_all.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/Archive/reco_scan.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/Archive/run_dch_chain.sh` | !/bin/bash | no |  |
| `test/testTrackFinder/Archive/simple_local_chain.sh` | !/bin/bash | no |  |
| `test/testTrackFinder/Archive/SimplerunDCHTestTrackFinder.py` | Return a local .onnx path for ONNXRuntime. | no |  |
| `test/testTrackFinder/Archive/skim_edm4hep.py` | !/usr/bin/env python3 | no |  |
| `test/testTrackFinder/Archive/SteeringFile_IDEA_o1_v03.py` | # The compact XML file, or multiple compact files, if the last one is the closer. | no |  |
| `test/testTrackFinder/Archive/SteeringFile_IDEA_o1_v03DCH.py` | dch_only_steer.py  — DCH-only DDSim steering (truth-friendly, robust) | no |  |
| `test/testTrackFinder/Archive/test_trackFinder_1.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/Archive/testcondor.sh` |  | no |  |
| `test/testTrackFinder/cglenn.cc` |  | no |  |
| `test/testTrackFinder/dd4hep2root.py` | !/usr/bin/env python3 | no |  |
| `test/testTrackFinder/filelist.txt` |  | no |  |
| `test/testTrackFinder/local_chain.sh` |  | yes |  |
| `test/testTrackFinder/params/job_0.json` |  | no |  |
| `test/testTrackFinder/params/job_1.json` |  | no |  |
| `test/testTrackFinder/params/job_10.json` |  | no |  |
| `test/testTrackFinder/params/job_100.json` |  | no |  |
| `test/testTrackFinder/params/job_101.json` |  | no |  |
| `test/testTrackFinder/params/job_102.json` |  | no |  |
| `test/testTrackFinder/params/job_103.json` |  | no |  |
| `test/testTrackFinder/params/job_104.json` |  | no |  |
| `test/testTrackFinder/params/job_105.json` |  | no |  |
| `test/testTrackFinder/params/job_106.json` |  | no |  |
| `test/testTrackFinder/params/job_107.json` |  | no |  |
| `test/testTrackFinder/params/job_108.json` |  | no |  |
| `test/testTrackFinder/params/job_109.json` |  | no |  |
| `test/testTrackFinder/params/job_11.json` |  | no |  |
| `test/testTrackFinder/params/job_110.json` |  | no |  |
| `test/testTrackFinder/params/job_111.json` |  | no |  |
| `test/testTrackFinder/params/job_112.json` |  | no |  |
| `test/testTrackFinder/params/job_113.json` |  | no |  |
| `test/testTrackFinder/params/job_114.json` |  | no |  |
| `test/testTrackFinder/params/job_115.json` |  | no |  |
| `test/testTrackFinder/params/job_116.json` |  | no |  |
| `test/testTrackFinder/params/job_117.json` |  | no |  |
| `test/testTrackFinder/params/job_118.json` |  | no |  |
| `test/testTrackFinder/params/job_119.json` |  | no |  |
| `test/testTrackFinder/params/job_12.json` |  | no |  |
| `test/testTrackFinder/params/job_13.json` |  | no |  |
| `test/testTrackFinder/params/job_14.json` |  | no |  |
| `test/testTrackFinder/params/job_15.json` |  | no |  |
| `test/testTrackFinder/params/job_16.json` |  | no |  |
| `test/testTrackFinder/params/job_17.json` |  | no |  |
| `test/testTrackFinder/params/job_18.json` |  | no |  |
| `test/testTrackFinder/params/job_19.json` |  | no |  |
| `test/testTrackFinder/params/job_2.json` |  | no |  |
| `test/testTrackFinder/params/job_20.json` |  | no |  |
| `test/testTrackFinder/params/job_21.json` |  | no |  |
| `test/testTrackFinder/params/job_22.json` |  | no |  |
| `test/testTrackFinder/params/job_23.json` |  | no |  |
| `test/testTrackFinder/params/job_24.json` |  | no |  |
| `test/testTrackFinder/params/job_25.json` |  | no |  |
| `test/testTrackFinder/params/job_26.json` |  | no |  |
| `test/testTrackFinder/params/job_27.json` |  | no |  |
| `test/testTrackFinder/params/job_28.json` |  | no |  |
| `test/testTrackFinder/params/job_29.json` |  | no |  |
| `test/testTrackFinder/params/job_3.json` |  | no |  |
| `test/testTrackFinder/params/job_30.json` |  | no |  |
| `test/testTrackFinder/params/job_31.json` |  | no |  |
| `test/testTrackFinder/params/job_32.json` |  | no |  |
| `test/testTrackFinder/params/job_33.json` |  | no |  |
| `test/testTrackFinder/params/job_34.json` |  | no |  |
| `test/testTrackFinder/params/job_35.json` |  | no |  |
| `test/testTrackFinder/params/job_36.json` |  | no |  |
| `test/testTrackFinder/params/job_37.json` |  | no |  |
| `test/testTrackFinder/params/job_38.json` |  | no |  |
| `test/testTrackFinder/params/job_39.json` |  | no |  |
| `test/testTrackFinder/params/job_4.json` |  | no |  |
| `test/testTrackFinder/params/job_40.json` |  | no |  |
| `test/testTrackFinder/params/job_41.json` |  | no |  |
| `test/testTrackFinder/params/job_42.json` |  | no |  |
| `test/testTrackFinder/params/job_43.json` |  | no |  |
| `test/testTrackFinder/params/job_44.json` |  | no |  |
| `test/testTrackFinder/params/job_45.json` |  | no |  |
| `test/testTrackFinder/params/job_46.json` |  | no |  |
| `test/testTrackFinder/params/job_47.json` |  | no |  |
| `test/testTrackFinder/params/job_48.json` |  | no |  |
| `test/testTrackFinder/params/job_49.json` |  | no |  |
| `test/testTrackFinder/params/job_5.json` |  | no |  |
| `test/testTrackFinder/params/job_50.json` |  | no |  |
| `test/testTrackFinder/params/job_51.json` |  | no |  |
| `test/testTrackFinder/params/job_52.json` |  | no |  |
| `test/testTrackFinder/params/job_53.json` |  | no |  |
| `test/testTrackFinder/params/job_54.json` |  | no |  |
| `test/testTrackFinder/params/job_55.json` |  | no |  |
| `test/testTrackFinder/params/job_56.json` |  | no |  |
| `test/testTrackFinder/params/job_57.json` |  | no |  |
| `test/testTrackFinder/params/job_58.json` |  | no |  |
| `test/testTrackFinder/params/job_59.json` |  | no |  |
| `test/testTrackFinder/params/job_6.json` |  | no |  |
| `test/testTrackFinder/params/job_60.json` |  | no |  |
| `test/testTrackFinder/params/job_61.json` |  | no |  |
| `test/testTrackFinder/params/job_62.json` |  | no |  |
| `test/testTrackFinder/params/job_63.json` |  | no |  |
| `test/testTrackFinder/params/job_64.json` |  | no |  |
| `test/testTrackFinder/params/job_65.json` |  | no |  |
| `test/testTrackFinder/params/job_66.json` |  | no |  |
| `test/testTrackFinder/params/job_67.json` |  | no |  |
| `test/testTrackFinder/params/job_68.json` |  | no |  |
| `test/testTrackFinder/params/job_69.json` |  | no |  |
| `test/testTrackFinder/params/job_7.json` |  | no |  |
| `test/testTrackFinder/params/job_70.json` |  | no |  |
| `test/testTrackFinder/params/job_71.json` |  | no |  |
| `test/testTrackFinder/params/job_72.json` |  | no |  |
| `test/testTrackFinder/params/job_73.json` |  | no |  |
| `test/testTrackFinder/params/job_74.json` |  | no |  |
| `test/testTrackFinder/params/job_75.json` |  | no |  |
| `test/testTrackFinder/params/job_76.json` |  | no |  |
| `test/testTrackFinder/params/job_77.json` |  | no |  |
| `test/testTrackFinder/params/job_78.json` |  | no |  |
| `test/testTrackFinder/params/job_79.json` |  | no |  |
| `test/testTrackFinder/params/job_8.json` |  | no |  |
| `test/testTrackFinder/params/job_80.json` |  | no |  |
| `test/testTrackFinder/params/job_81.json` |  | no |  |
| `test/testTrackFinder/params/job_82.json` |  | no |  |
| `test/testTrackFinder/params/job_83.json` |  | no |  |
| `test/testTrackFinder/params/job_84.json` |  | no |  |
| `test/testTrackFinder/params/job_85.json` |  | no |  |
| `test/testTrackFinder/params/job_86.json` |  | no |  |
| `test/testTrackFinder/params/job_87.json` |  | no |  |
| `test/testTrackFinder/params/job_88.json` |  | no |  |
| `test/testTrackFinder/params/job_89.json` |  | no |  |
| `test/testTrackFinder/params/job_9.json` |  | no |  |
| `test/testTrackFinder/params/job_90.json` |  | no |  |
| `test/testTrackFinder/params/job_91.json` |  | no |  |
| `test/testTrackFinder/params/job_92.json` |  | no |  |
| `test/testTrackFinder/params/job_93.json` |  | no |  |
| `test/testTrackFinder/params/job_94.json` |  | no |  |
| `test/testTrackFinder/params/job_95.json` |  | no |  |
| `test/testTrackFinder/params/job_96.json` |  | no |  |
| `test/testTrackFinder/params/job_97.json` |  | no |  |
| `test/testTrackFinder/params/job_98.json` |  | no |  |
| `test/testTrackFinder/params/job_99.json` |  | no |  |
| `test/testTrackFinder/runDCHTestTrackFinder.py` |  | yes |  |
| `test/testTrackFinder/runTestTrackFinder.py` | ################# Parser | no |  |
| `test/testTrackFinder/scripts/analyze_job.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/scripts/analyze_pt_resolution_grid.py` |  | yes |  |
| `test/testTrackFinder/scripts/autoreadme.py` |  | yes |  |
| `test/testTrackFinder/scripts/Calculate_Aucoating_thickness.py` | Calculate_Aucoating_thickness.py | no |  |
| `test/testTrackFinder/scripts/cglenn.cc` |  | no |  |
| `test/testTrackFinder/scripts/compact_path.txt` |  | no |  |
| `test/testTrackFinder/scripts/compare_pt_resolution_grid.py` |  | yes |  |
| `test/testTrackFinder/scripts/condor_ddsim.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/scripts/condor_reco.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/scripts/debug_z_spur_event.py` | DOC | no |  |
| `test/testTrackFinder/scripts/DelphesParamsOutput.py` | extract_delphes_tracker_params.py | no |  |
| `test/testTrackFinder/scripts/dump_covmatrix_one_event.py` |  | yes |  |
| `test/testTrackFinder/scripts/filelist.txt` |  | no |  |
| `test/testTrackFinder/scripts/inspect_events_pt_pathology.py` | !/usr/bin/env python3 | no |  |
| `test/testTrackFinder/scripts/make_filelist.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/scripts/make_runtime.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/scripts/mk_ddsim_grid.py` | !/usr/bin/env python3 | no |  |
| `test/testTrackFinder/scripts/patch_trkCov_match_dch_material.py` | Example: | no |  |
| `test/testTrackFinder/scripts/plot_mcparticles_pt.py` |  | yes |  |
| `test/testTrackFinder/scripts/plot_pt_from_trackstate_time.py` |  | yes |  |
| `test/testTrackFinder/scripts/prepare_and_submit.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/scripts/print_metadata.py` | !/usr/bin/env python3 | no |  |
| `test/testTrackFinder/scripts/queue_items.txt` |  | no |  |
| `test/testTrackFinder/scripts/reco_job.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/scripts/scan_pt_time_by_event.py` |  | yes |  |
| `test/testTrackFinder/scripts/stamp_ddsim_metadata.py` | !/usr/bin/env python3 | no |  |
| `test/testTrackFinder/scripts/stamp_pipeline_metadata.py` | !/usr/bin/env python3 | no |  |
| `test/testTrackFinder/scripts/submit_reco.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/scripts/sweep_pt.sh` | !/usr/bin/env bash | no |  |
| `test/testTrackFinder/scripts/view_simhits_event.py` |  | yes |  |
| `test/testTrackFinder/scripts/view_tracks_event.py` |  | yes |  |
| `test/testTrackFinder/test_trackFinder.sh` | !/bin/bash | no |  |
| `test/testTrackFinder/tracker_params.json` |  | no |  |
| `test/testTracksFromGenParticles/runTracksFromGenParticles.py` | Loading the output of the SIM step | no |  |
| `test/testTracksFromGenParticles/test_TracksFromGenParticles.sh` | !/bin/bash | no |  |
