#!/usr/bin/env python3
"""
debug_z_spur_event.py

Small EDM4hep inspection script to debug "z-spur" events.
"""

import argparse
import os

import matplotlib.pyplot as plt

from podio import root_io


def _has_collection(event, name: str) -> bool:
  """Return True if the podio Frame has a collection called `name`."""
  if not name:
    return False
  try:
    cols = event.getAvailableCollections()
    if name in cols:
      return True
  except Exception:
    # Fall back to probing get()
    try:
      event.get(name)
      return True
    except Exception:
      return False
  return False


def guess_wire_collection(event, user_wire_coll):
  if user_wire_coll and _has_collection(event, user_wire_coll):
    return user_wire_coll

  candidates = [
      "DCHDigi2Collection",  # v02
      "DCH_DigiCollection",  # v01
      "DCHDigiCollection",   # other variants
  ]
  for name in candidates:
    if _has_collection(event, name):
      print(f"[guess] Using wire collection: {name}")
      return name

  raise RuntimeError(
      f"No wire digi collection found. Tried user='{user_wire_coll}' "
      f"and {candidates}"
  )


def guess_link_collection(event, user_link_coll):
  if user_link_coll and _has_collection(event, user_link_coll):
    return user_link_coll

  candidates = [
      "DCHDigi2SimLinkCollection",  # v02
      "DCHDigiSimLinkCollection",   # generic
  ]
  for name in candidates:
    if _has_collection(event, name):
      print(f"[guess] Using link collection: {name}")
      return name

  raise RuntimeError(
      f"No SenseWireHitSimTrackerHit link collection found. "
      f"Tried user='{user_link_coll}' and {candidates}"
  )


def guess_mc_collection(event, user_mc_coll):
  if user_mc_coll and _has_collection(event, user_mc_coll):
    return user_mc_coll

  candidates = [
      "MCParticles",
      "MCParticle",
  ]
  for name in candidates:
    if _has_collection(event, name):
      print(f"[guess] Using MCParticles collection: {name}")
      return name

  print("[warn] No MCParticles collection found; will just use "
        "SimTrackerHit.getParticle() handles.")
  return None


def build_sw_to_mc_map(links):
  sw_to_mc = {}
  for link in links:
    sw = link.getFrom()  # SenseWireHit
    sh = link.getTo()    # SimTrackerHit
    mcp = sh.getParticle()

    sw_oid  = sw.getObjectID()
    mcp_oid = mcp.getObjectID()

    key = (sw_oid.index, sw_oid.collectionID)
    value = {
        "mc_index": mcp_oid.index,
        "mc_collID": mcp_oid.collectionID,
        "simhit": sh,
    }
    sw_to_mc[key] = value
  return sw_to_mc


def analyze_event(event,
                  wire_coll_name,
                  link_coll_name,
                  mc_coll_name,
                  png_out,
                  z_cut=None):
  wire_hits = event.get(wire_coll_name)
  links     = event.get(link_coll_name)

  if mc_coll_name and _has_collection(event, mc_coll_name):
    mcparts = event.get(mc_coll_name)
  else:
    mcparts = None

  print(f"[evt] wire_hits: {wire_coll_name} size = {wire_hits.size()}")
  print(f"[evt] links:      {link_coll_name} size = {links.size()}")

  if wire_hits.size() == 0:
    print("[evt] No wire hits; nothing to do.")
    return

  sw_to_mc = build_sw_to_mc_map(links)

  zs, ts = [], []
  mc_ids_for_point = []
  mc_summary = {}

  for sw in wire_hits:
    pos = sw.getPosition()
    z   = pos.z
    t   = sw.getTime()

    sw_oid = sw.getObjectID()
    key = (sw_oid.index, sw_oid.collectionID)
    mcf = sw_to_mc.get(key, None)

    if mcf is None:
      mc_key = None
    else:
      mc_key = (mcf["mc_index"], mcf["mc_collID"])

    if z_cut is not None and not (z_cut[0] <= z <= z_cut[1]):
      continue

    zs.append(z)
    ts.append(t)
    mc_ids_for_point.append(mc_key)

    if mc_key is not None:
      if mc_key not in mc_summary:
        mc_summary[mc_key] = {
            "nhits": 0,
            "zmin": z,
            "zmax": z,
            "tmin": t,
            "tmax": t,
        }
      s = mc_summary[mc_key]
      s["nhits"] += 1
      s["zmin"] = min(s["zmin"], z)
      s["zmax"] = max(s["zmax"], z)
      s["tmin"] = min(s["tmin"], t)
      s["tmax"] = max(s["tmax"], t)

  print("\n[summary] MCParticle contributions (via links):")
  if not mc_summary:
    print("  No links from digis to MCParticles found.")
  else:
    for (idx, collID), s in sorted(mc_summary.items(),
                                   key=lambda kv: kv[1]["nhits"],
                                   reverse=True):
      line = (f"  MC(index={idx}, collID={collID}) : "
              f"nhits={s['nhits']}, "
              f"z=[{s['zmin']:.1f}, {s['zmax']:.1f}] mm, "
              f"t=[{s['tmin']:.2f}, {s['tmax']:.2f}] ns")
      if mcparts is not None and 0 <= idx < mcparts.size():
        mcp = mcparts[idx]
        try:
          pdg = mcp.getPDG()
        except Exception:
          pdg = "?"
        line += f", PDG={pdg}"
      print(line)

  if not zs:
    print("[plot] No hits after z_cut; skipping time vs z scatter.")
    return

  mc_to_color = {}
  next_color = 0
  colors = []
  for mc_key in mc_ids_for_point:
    if mc_key is None:
      key = ("unlinked", -1)
    else:
      key = mc_key
    if key not in mc_to_color:
      mc_to_color[key] = next_color
      next_color += 1
    colors.append(mc_to_color[key])

  plt.figure(figsize=(7, 5))
  plt.scatter(zs, ts, c=colors, s=10, alpha=0.8)
  plt.xlabel("z [mm]")
  plt.ylabel("time [ns]")
  if z_cut is not None:
    plt.title(f"Event time vs z (wire digis, z in [{z_cut[0]}, {z_cut[1]}])")
  else:
    plt.title("Event time vs z (wire digis)")

  max_legend = 10
  handles = []
  labels = []
  cmap = plt.cm.get_cmap("tab20", max(next_color, 1))

  for i, (mc_key, color_idx) in enumerate(mc_to_color.items()):
    if i >= max_legend:
      break
    if mc_key == ("unlinked", -1):
      mc_label = "unlinked"
    else:
      mc_index, collID = mc_key
      mc_label = f"MC idx={mc_index}, collID={collID}"
      if mcparts is not None and 0 <= mc_index < mcparts.size():
        try:
          pdg = mcparts[mc_index].getPDG()
          mc_label += f", PDG={pdg}"
        except Exception:
          pass
    handles.append(
        plt.Line2D([0], [0], marker="o", linestyle="",
                   color=cmap(color_idx), markersize=6)
    )
    labels.append(mc_label)

  if handles:
    plt.legend(handles, labels, loc="best", fontsize=7)

  os.makedirs(os.path.dirname(png_out) or ".", exist_ok=True)
  plt.tight_layout()
  plt.savefig(png_out, dpi=150)
  plt.close()

  print(f"[plot] Saved time-vs-z scatter to: {png_out}")


def main():
  ap = argparse.ArgumentParser(
      description="Debug one event's DCH digis vs MCParticles (time vs z)."
  )
  ap.add_argument("--input", required=True,
                  help="EDM4hep ROOT file (same as for view_tracks_event.py)")
  ap.add_argument("--event", type=int, required=True,
                  help="Event index (0-based, same as in view_tracks_event.py)")
  ap.add_argument("--wire-coll", default="",
                  help="SenseWireHit collection name "
                       "(default: auto-detect; e.g. DCHDigi2Collection)")
  ap.add_argument("--link-coll", default="",
                  help="SenseWireHitSimTrackerHitLink collection name "
                       "(default: auto-detect; e.g. DCHDigi2SimLinkCollection)")
  ap.add_argument("--mc-coll", default="",
                  help="MCParticles collection name (default: auto-detect)")
  ap.add_argument("--z-min", type=float, default=None,
                  help="Optional z-min mm for focusing on spur region")
  ap.add_argument("--z-max", type=float, default=None,
                  help="Optional z-max mm for focusing on spur region")
  ap.add_argument("--png", default="",
                  help="Output PNG for time-vs-z plot "
                       "(default: <input>_evt<event>_time_vs_z.png)")

  args = ap.parse_args()

  if not os.path.exists(args.input):
    raise SystemExit(f"Input file not found: {args.input}")

  reader = root_io.Reader(args.input)
  events = reader.get("events")

  n_events = len(events)
  print(f"[file] {args.input} : nEvents = {n_events}")
  if args.event < 0 or args.event >= n_events:
    raise SystemExit(f"Requested event={args.event} out of range [0,{n_events-1}]")

  event = events[args.event]
  print(f"[evt] Inspecting event index = {args.event}")
  try:
    print("[evt] available collections:", event.getAvailableCollections())
  except Exception:
    pass

  wire_coll_name = guess_wire_collection(event, args.wire_coll)
  link_coll_name = guess_link_collection(event, args.link_coll)
  mc_coll_name   = guess_mc_collection(event, args.mc_coll)

  if args.png:
    png_out = args.png
  else:
    base = os.path.splitext(os.path.basename(args.input))[0]
    png_out = f"{base}_evt{args.event}_time_vs_z.png"

  z_cut = None
  if args.z_min is not None and args.z_max is not None:
    z_cut = (args.z_min, args.z_max)

  analyze_event(event, wire_coll_name, link_coll_name, mc_coll_name,
                png_out, z_cut)

  # No .close() on this Reader in your version; just drop it.
  del reader


if __name__ == "__main__":
  main()
