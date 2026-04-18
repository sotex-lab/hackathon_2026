"""
Test/demo script for fetch_dt.py

Run:
    python3 test_fetch_dt.py

This demonstrates how to import and use the fetch_dt module
from other parts of the application.
"""

import pandas as pd
from fetch_dt import get_dt_readings_24h, get_dt_info, list_active_dts


def section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# ------------------------------------------------------------------
# TEST 1: list all active DTs
# ------------------------------------------------------------------
section("TEST 1 — list_active_dts()")
dts = list_active_dts()

print(f"Total active DTs: {len(dts)}")
print(f"Columns: {list(dts.columns)}")
print(f"\nFirst 5 rows:")
print(dts.head().to_string(index=False))

assert isinstance(dts, pd.DataFrame), "Expected a DataFrame"
assert set(dts.columns) == {"id", "name", "meter_id", "last_reading"}, \
    "Unexpected columns"
assert len(dts) > 0, "Expected at least one active DT"
print("\n✓ list_active_dts() works")


# ------------------------------------------------------------------
# TEST 2: get info about a specific DT
# ------------------------------------------------------------------
section("TEST 2 — get_dt_info(dt_id)")

test_dt_id = int(dts.iloc[0]["id"])
info = get_dt_info(test_dt_id)

print(f"Info for DT id={test_dt_id}:")
for k, v in info.items():
    print(f"  {k}: {v}")

assert info is not None
assert info["id"] == test_dt_id
assert set(info.keys()) == {
    "id", "name", "meter_id", "latitude", "longitude", "nameplate_kva"
}
print("\n✓ get_dt_info() works")


# ------------------------------------------------------------------
# TEST 3: get readings for a specific DT
# ------------------------------------------------------------------
section("TEST 3 — get_dt_readings_24h(dt_id)")

readings = get_dt_readings_24h(test_dt_id)

assert readings is not None, f"No readings for DT {test_dt_id}"
print(f"Readings for DT id={test_dt_id}:")
print(f"  Rows: {len(readings)}")
print(f"  Columns: {list(readings.columns)}")
print(f"  Time range: {readings['Ts'].min()} -> {readings['Ts'].max()}")
print(f"\nFirst 5 rows:")
print(readings.head().to_string(index=False))

expected_cols = {"Ts", "V_a", "V_b", "V_c", "I_a", "I_b", "I_c"}
assert set(readings.columns) == expected_cols, f"Got {readings.columns}"
assert len(readings) > 0
print("\n✓ get_dt_readings_24h() works")


# ------------------------------------------------------------------
# TEST 4: non-existent DT returns None
# ------------------------------------------------------------------
section("TEST 4 — non-existent DT returns None")

missing_info = get_dt_info(999_999_999)
missing_readings = get_dt_readings_24h(999_999_999)

print(f"get_dt_info(999999999)         -> {missing_info}")
print(f"get_dt_readings_24h(999999999) -> {missing_readings}")

assert missing_info is None
assert missing_readings is None
print("\n✓ missing DT handled gracefully")


# ------------------------------------------------------------------
# TEST 5: example workflow for a teammate building the UI
# ------------------------------------------------------------------
section("TEST 5 — example usage pattern (teammate building UI)")

# Step 1: get the list of DTs -> populate dropdown
dt_list = list_active_dts()

# Step 2: user picks a DT by name (e.g. from a dropdown)
chosen_name = dt_list.iloc[0]["name"]
print(f"User picked: {chosen_name!r}")

chosen_id = int(dt_list[dt_list["name"] == chosen_name].iloc[0]["id"])

# Step 3: fetch readings + info
readings = get_dt_readings_24h(chosen_id)
info = get_dt_info(chosen_id)

# Step 4: hand off to the chart / map module
if readings is None:
    print("No data — UI should show 'No readings available'.")
else:
    print(f"Ready to plot: {len(readings)} points, DT {info['name']!r}")
    print(f"Location: ({info['latitude']}, {info['longitude']})")
    print(f"Nameplate: {info['nameplate_kva']} kVA")
    print(f"\nData ready for chart:")
    print(readings.head(3).to_string(index=False))


# ------------------------------------------------------------------
# DONE
# ------------------------------------------------------------------
section("ALL TESTS PASSED ✓")
print("The fetch_dt module is ready to import from other files.")