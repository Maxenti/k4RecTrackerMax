# DOC:
# Summary: Convert compact DD4hep XML geometry descriptions into a TGeo ROOT geometry file for material-aware GenFit/reco workflows.
# Status: authoritative
# Usage:
#   python3 steering/dd4hep2root.py -c COMPACT.xml -o GEOMETRY.root
#   python3 steering/dd4hep2root.py -c BASE.xml VARIANT.xml -o VARIANT.root
# Examples:
#   python3 steering/dd4hep2root.py \
#     -c /eos/.../IDEA_o1_v03CF_2umAu.xml \
#     -o /eos/.../IDEA_o1_v03CF_2umAu.root
#   Expected result: a ROOT file containing the exported TGeo geometry from ROOT.gGeoManager.
# Inputs: One or more compact DD4hep XML files readable by dd4hep.Detector.fromXML().
# Outputs: A TGeo ROOT geometry file written by ROOT.gGeoManager.Export(out_path).
# Collections: None; this is a geometry conversion utility, not an EDM4hep event/collection processor.
# Connects-To: steering/runDCHTestTrackFinder.py, steering/local_chain.sh, scripts/submit_reco.sh, scripts/reco_job.sh, configs/geom/compact.xml
# Arguments:
#   -c, --compact: required list of compact DD4hep XML files to load in order with dd4hep.Detector.fromXML().
#   -o, --out: output TGeo ROOT file path; default detector.root.
# Notes:
#   Use this when a material/reco campaign needs a TGeo ROOT geometry matching the compact XML passed to GeoSvc.
#   For GenFit material-aware comparisons, the compact XML and exported TGeo ROOT file must correspond to the same detector/material variant.
#   This script loads libDDCore, fills the global DD4hep detector description, then exports ROOT.gGeoManager.
#   If multiple compact XML files are passed, they are loaded sequentially into the same dd4hep.Detector instance.
#   The output is a generated geometry artifact; long-term outputs should live under artifacts/geometry/ or EOS, not mixed into active source directories.
# Tags: authoritative, geometry, dd4hep, tgeo, root, genfit2, material-effects, converter
# DOC_END

#!/usr/bin/env python3

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description='Convert detector')
    parser.add_argument('-c', '--compact', help='Compact file location(s)',
                        required=True, type=str, nargs='+')
    parser.add_argument('-o', '--out', help='Converted file path',
                        default='detector.root', type=str)
    args = vars(parser.parse_args())

    convert(args['compact'], args['out'])


def convert(compact_files, out_path):
    print('INFO: Converting following compact file(s):')
    for cfile in compact_files:
        print('      ' + cfile)

    import ROOT

    ROOT.gSystem.Load('libDDCore')
    description = ROOT.dd4hep.Detector.getInstance()
    for cfile in compact_files:
        description.fromXML(cfile)

    ROOT.gGeoManager.SetVisLevel(9)
    ROOT.gGeoManager.SetVisOption(0)
    ROOT.gGeoManager.Export(out_path)


if __name__ == '__main__':
    main()
