# test/testTrackFinder

This README is auto-generated from per-file `DOC:` blocks (preferred) plus heuristics.
Improve accuracy by adding a `DOC:` header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `.__afs724E` |  |  |  |  |
| ⚠️ `cglenn.cc` |  |  |  |  |
| ⚠️ `dd4hep2root.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:argparse<br>import:sys |
| ⚠️ `filelist.txt` |  |  |  |  |
| ⚠️ `local_chain.sh` | !/bin/bash |  |  | calls:runDCHTestTrackFinder.py<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:Tracks<br>uses:k4run |
| ⚠️ `runDCHTestTrackFinder.py` | Return a set of property names, or None if not introspectable. |  |  | gaudi:imports:Configurables<br>gaudi:topalg:CDCHTracks<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:DCHDigi2SimLink<br>gaudi:topalg:DCHDigi2SimLinkCollection<br>gaudi:topalg:DCHDigiSimLink<br>gaudi:topalg:DCHDigiSimLinkCollection<br>gaudi:topalg:DCHName<br>gaudi:topalg:DCHSimHits |
| ⚠️ `runTestTrackFinder.py` | ################# Parser |  |  | gaudi:imports:Configurables<br>gaudi:topalg:CDCHTracks<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_DigiCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:DCHdigi<br>gaudi:topalg:GGTF_tracking<br>import:Configurables<br>import:Gaudi.Configuration<br>import:k4FWCore |
| ⚠️ `test_trackFinder.sh` | !/bin/bash |  |  | uses:k4run |
