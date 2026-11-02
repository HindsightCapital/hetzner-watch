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

CITY = {"fsn1": "Falkenstein", "nbg1": "Nuremberg", "hel1": "Helsinki",
        "ash": "Ashburn", "hil": "Hillsboro", "sin": "Singapore"}

# Since Oct 2026 availability lives on server_types[].locations[].available
# (the old /datacenters endpoint returns 410 Gone).
now = set()
page = 1
while page:
    data = get(f"/server_types?per_page=50&page={page}")
    for t in data["server_types"]:
        if t["name"] in WANT:
            print(t["name"], "locations:", [(l.get("name"), l.get("available")) for l in t.get("locations", [])])
            for loc in t.get("locations", []):
                if loc.get("available"):
                    name = loc.get("name", "?")
                    now.add(f'{t["name"].upper()} in {CITY.get(name, name)} ({name})')
    page = (data.get("meta", {}).get("pagination") or {}).get("next_page")

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
