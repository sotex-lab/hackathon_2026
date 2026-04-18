"""
Test/demo script for fetch_ts.py and fetch_ss.py.

Run:
    python3 test_fetch_ts_ss.py
"""

import pandas as pd
from fetch_ts import get_ts_info, get_ts_feeders, get_ts_readings_24h, list_transmission_stations
from fetch_ss import get_ss_info, get_ss_feeders, get_ss_readings_24h, list_substations


def section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# ------------------------------------------------------------------
section("TEST 1 — list_transmission_stations()")
tss = list_transmission_stations()
print(f"Total TSs: {len(tss)}")
print(tss.head().to_string(index=False))
assert len(tss) > 0


# ------------------------------------------------------------------
section("TEST 2 — list_substations()")
sss = list_substations()
print(f"Total SSs: {len(sss)}")
print(sss.head().to_string(index=False))
assert len(sss) > 0


# ------------------------------------------------------------------
section("TEST 3 — find a TS that has feeders with readings")

chosen_ts_id = None
for ts_id in tss["id"].tolist():
    fs = get_ts_feeders(int(ts_id))
    if len(fs["F33"]) + len(fs["F11_trade"]) > 0:
        chosen_ts_id = int(ts_id)
        break

assert chosen_ts_id is not None, "No TS with any feeders found"
print(f"Picked TS id={chosen_ts_id}")

info = get_ts_info(chosen_ts_id)
print(f"Info: {info}")
assert info is not None


# ------------------------------------------------------------------
section(f"TEST 4 — get_ts_readings_24h({chosen_ts_id})")

bundle = get_ts_readings_24h(chosen_ts_id)
assert bundle is not None

print(f"TS '{bundle['info']['name']}'")
print(f"  F33 count:       {len(bundle['F33'])}")
print(f"  F11 trade count: {len(bundle['F11_trade'])}")

if bundle["F33"]:
    f = bundle["F33"][0]
    print(f"\nFirst F33 feeder — [{f['id']}] {f['name']}")
    if f["readings"] is not None:
        print(f"  rows:    {len(f['readings'])}")
        print(f"  columns: {list(f['readings'].columns)}")
        print("\n  First 3 rows:")
        print(f["readings"].head(3).to_string(index=False))
    else:
        print("  No readings.")


# ------------------------------------------------------------------
section("TEST 5 — find an SS that has feeders with readings")

chosen_ss_id = None
for ss_id in sss["id"].tolist():
    fs = get_ss_feeders(int(ss_id))
    if len(fs["F33_incoming"]) + len(fs["F11_outgoing"]) > 0:
        chosen_ss_id = int(ss_id)
        break

assert chosen_ss_id is not None, "No SS with any feeders found"
print(f"Picked SS id={chosen_ss_id}")


# ------------------------------------------------------------------
section(f"TEST 6 — get_ss_readings_24h({chosen_ss_id})")

bundle = get_ss_readings_24h(chosen_ss_id)
assert bundle is not None

print(f"SS '{bundle['info']['name']}'")
print(f"  F33 incoming: {len(bundle['F33_incoming'])}")
print(f"  F11 outgoing: {len(bundle['F11_outgoing'])}")

for kind in ("F33_incoming", "F11_outgoing"):
    if bundle[kind]:
        f = bundle[kind][0]
        print(f"\nFirst {kind} — [{f['id']}] {f['name']}")
        if f["readings"] is not None:
            print(f"  rows:    {len(f['readings'])}")
            print(f"  columns: {list(f['readings'].columns)}")


# ------------------------------------------------------------------
section("TEST 7 — missing TS/SS returns None")

assert get_ts_info(999_999_999) is None
assert get_ss_info(999_999_999) is None
assert get_ts_readings_24h(999_999_999) is None
assert get_ss_readings_24h(999_999_999) is None
print("✓ missing IDs handled gracefully")


section("ALL TESTS PASSED ✓")
print("Modules ready. Import:")
print("  from fetch_ts import get_ts_info, get_ts_feeders, get_ts_readings_24h")
print("  from fetch_ss import get_ss_info, get_ss_feeders, get_ss_readings_24h")