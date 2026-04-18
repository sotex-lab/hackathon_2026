"""
Test/demo script for fetch_dt.py

Run:
    python3 test_fetch_dt.py

Demonstrates how to import and use fetch_dt from other modules
(e.g. the UI / charting module).
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
# TEST 3: get readings for a specific DT (V/I + kWh combined)
# ------------------------------------------------------------------
section("TEST 3 — get_dt_readings_24h(dt_id)")

readings = get_dt_readings_24h(test_dt_id)

assert readings is not None, f"No readings for DT {test_dt_id}"
print(f"Readings for DT id={test_dt_id}:")
print(f"  Rows: {len(readings)}")
print(f"  Columns: {list(readings.columns)}")
print(f"  Time range: {readings['Ts'].min()} -> {readings['Ts'].max()}")

# quick count of how much data each category has
voltage_rows = readings[["V_a", "V_b", "V_c"]].notna().any(axis=1).sum()
current_rows = readings[["I_a", "I_b", "I_c"]].notna().any(axis=1).sum()
kwh_rows = readings["kwh"].notna().sum()
print(f"  Rows with any voltage: {voltage_rows}")
print(f"  Rows with any current: {current_rows}")
print(f"  Rows with kwh:         {kwh_rows}")

print(f"\nFirst 5 rows:")
print(readings.head().to_string(index=False))

expected_cols = {"Ts", "V_a", "V_b", "V_c", "I_a", "I_b", "I_c", "kwh"}
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
#         (3 separate charts: voltage, current, kWh)
# ------------------------------------------------------------------
section("TEST 5 — example usage pattern (3 charts for UI)")

# Step 1: populate dropdown
dt_list = list_active_dts()
chosen_name = dt_list.iloc[0]["name"]
chosen_id = int(dt_list[dt_list["name"] == chosen_name].iloc[0]["id"])
print(f"User picked: {chosen_name!r}  (id={chosen_id})")

# Step 2: fetch readings + info
readings = get_dt_readings_24h(chosen_id)
info = get_dt_info(chosen_id)

if readings is None:
    print("No data — UI should show 'No readings available'.")
else:
    print(f"\nInfo for chart header:")
    print(f"  DT:         {info['name']}")
    print(f"  Location:   ({info['latitude']}, {info['longitude']})")
    print(f"  Nameplate:  {info['nameplate_kva']} kVA")

    # Three separate data slices for three charts
    voltage_chart = readings[["Ts", "V_a", "V_b", "V_c"]].dropna(
        subset=["V_a", "V_b", "V_c"], how="all"
    )
    current_chart = readings[["Ts", "I_a", "I_b", "I_c"]].dropna(
        subset=["I_a", "I_b", "I_c"], how="all"
    )
    kwh_chart = readings[["Ts", "kwh"]].dropna(subset=["kwh"])

    print(f"\nChart 1 — Voltage: {len(voltage_chart)} points")
    print(voltage_chart.head(3).to_string(index=False))

    print(f"\nChart 2 — Current: {len(current_chart)} points")
    print(current_chart.head(3).to_string(index=False))

    print(f"\nChart 3 — kWh:     {len(kwh_chart)} points")
    print(kwh_chart.head(3).to_string(index=False))


# ------------------------------------------------------------------
# DONE
# ------------------------------------------------------------------
section("ALL TESTS PASSED ✓")
print("The fetch_dt module is ready to import from other files.")