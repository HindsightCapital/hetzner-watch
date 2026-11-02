#!/usr/bin/env python3
"""Hetzner Cloud availability watcher for CX33 / CX43.
Needs: HCLOUD_TOKEN (read-only API token), NTFY_TOPIC (any hard-to-guess name).
Alerts once when a type becomes available in a location, and once when it goes away again.
"""
import json, os, urllib.request

WANT = {"cx33", "cx43"}
API = "https://api.hetzner.cloud/v1"
STATE = os.environ.get("STATE_FILE", "hetzner_state.json")

def get(path):
    req = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + os.environ["HCLOUD_TOKEN"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

types = {t["id"]: t["name"] for t in get("/server_types?per_page=50")["server_types"]}
now = set()
for dc in get("/datacenters?per_page=50")["datacenters"]:
    for tid in dc["server_types"]["available"]:
        if types.get(tid) in WANT:
            now.add(f'{types[tid].upper()} in {dc["location"]["city"]} ({dc["name"]})')

try:
    before = set(json.load(open(STATE)))
except Exception:
    before = set()

new, gone = sorted(now - before), sorted(before - now)
msg = []
if new:  msg.append("AVAILABLE: " + ", ".join(new))
if gone: msg.append("Gone again: " + ", ".join(gone))
if msg:
    urllib.request.urlopen(urllib.request.Request(
        "https://ntfy.sh/" + os.environ["NTFY_TOPIC"], data="\n".join(msg).encode(),
        headers={"Title": "Hetzner CX", "Priority": "high"}), timeout=30)
json.dump(sorted(now), open(STATE, "w"))
print("\n".join(msg) or "no change: " + (", ".join(sorted(now)) or "none available"))
