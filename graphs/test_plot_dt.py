"""
graphs/test_plot_dt.py

Testira plot_dt.py na realnim edge case-ovima iz baze:
 - DT sa najviše merenja (idealan)
 - DT sa najmanje merenja (retki podaci)
 - DT sa srednjom pokrivenošću
 - DT sa NULL MeterId
 - DT koji ne postoji
 - DT bez ijednog očitavanja
 - DT sa kWh podacima ali bez V/I
 - DT sa V/I ali bez kWh

Pokretanje iz root foldera:
    python3 graphs/test_plot_dt.py
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "get_data"))

import pandas as pd
from db import q
from fetch_dt import get_dt_readings_24h, get_dt_info
from plot_dt import nacrtaj, pripremi, kvalitet_podataka


def section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_dt(dt_id, label, expected=None):
    """
    Pokusa da pripremi podatke i nacrta graf za dati dt_id.
    Ne pada ako je problem — beleži šta se desilo.
    """
    print(f"\n── {label} (dt_id={dt_id})")
    try:
        info = get_dt_info(dt_id)
        if info is None:
            print(f"   INFO:       None (DT ne postoji)")
        else:
            print(f"   INFO:       {info['name']}, nameplate={info.get('nameplate_kva')}")

        df = get_dt_readings_24h(dt_id)
        if df is None:
            print(f"   READINGS:   None (nema merenja)")
        else:
            d = pripremi(df)
            k = kvalitet_podataka(d)
            print(f"   READINGS:   {k['ukupno']} redova, {k['sati']}h pokriveno")
            print(f"   VALID:      V={k['valid_v']}, I={k['valid_i']}, kWh={k['valid_e']}")

        # Najbitnije — grafik mora da se napravi bez greške
        fig = nacrtaj(dt_id)
        n_frames = len(fig.frames) if fig.frames else 0
        print(f"   GRAF:       OK, {n_frames} frame-ova animacije")

        if expected:
            print(f"   OČEKIVANO:  {expected}")

        return True, None
    except Exception as e:
        print(f"   ❌ PAO: {type(e).__name__}: {e}")
        return False, e


# ─────────────────────────────────────────────
# Nađi kandidat-DT-ove po različitim kriterijumima
# ─────────────────────────────────────────────

section("Priprema kandidata za testove")

# 1. Najviše merenja u 24h
best = q("""
    WITH meter_last AS (SELECT Mid, MAX(Ts) AS last_ts FROM MeterReads GROUP BY Mid),
         counts AS (
            SELECT mr.Mid, COUNT(*) AS cnt FROM MeterReads mr
            JOIN meter_last ml ON mr.Mid = ml.Mid
            WHERE mr.Ts > DATEADD(HOUR, -24, ml.last_ts)
            GROUP BY mr.Mid
         )
    SELECT TOP 1 dt.Id, c.cnt
    FROM DistributionSubstation dt JOIN counts c ON dt.MeterId = c.Mid
    ORDER BY c.cnt DESC
""")
best_dt_id = int(best.iloc[0]["Id"]) if not best.empty else None
print(f"Najbolji DT:     {best_dt_id} ({best.iloc[0]['cnt'] if not best.empty else '-'} merenja)")

# 2. Najmanje merenja u 24h (ali >0)
worst = q("""
    WITH meter_last AS (SELECT Mid, MAX(Ts) AS last_ts FROM MeterReads GROUP BY Mid),
         counts AS (
            SELECT mr.Mid, COUNT(*) AS cnt FROM MeterReads mr
            JOIN meter_last ml ON mr.Mid = ml.Mid
            WHERE mr.Ts > DATEADD(HOUR, -24, ml.last_ts)
            GROUP BY mr.Mid
         )
    SELECT TOP 1 dt.Id, c.cnt
    FROM DistributionSubstation dt JOIN counts c ON dt.MeterId = c.Mid
    WHERE c.cnt >= 1
    ORDER BY c.cnt ASC
""")
worst_dt_id = int(worst.iloc[0]["Id"]) if not worst.empty else None
print(f"Najsiromasniji:  {worst_dt_id} ({worst.iloc[0]['cnt'] if not worst.empty else '-'} merenja)")

# 3. Srednja pokrivenost
mid = q("""
    WITH meter_last AS (SELECT Mid, MAX(Ts) AS last_ts FROM MeterReads GROUP BY Mid),
         counts AS (
            SELECT mr.Mid, COUNT(*) AS cnt FROM MeterReads mr
            JOIN meter_last ml ON mr.Mid = ml.Mid
            WHERE mr.Ts > DATEADD(HOUR, -24, ml.last_ts)
            GROUP BY mr.Mid
         )
    SELECT TOP 1 dt.Id, c.cnt
    FROM DistributionSubstation dt JOIN counts c ON dt.MeterId = c.Mid
    WHERE c.cnt BETWEEN 20 AND 40
    ORDER BY c.cnt DESC
""")
mid_dt_id = int(mid.iloc[0]["Id"]) if not mid.empty else None
print(f"Srednji DT:      {mid_dt_id} ({mid.iloc[0]['cnt'] if not mid.empty else '-'} merenja)")

# 4. DT sa MeterId=None
no_meter = q("""
    SELECT TOP 1 Id FROM DistributionSubstation WHERE MeterId IS NULL
""")
no_meter_dt_id = int(no_meter.iloc[0]["Id"]) if not no_meter.empty else None
print(f"Bez MeterId:     {no_meter_dt_id}")

# 5. DT koji ima MeterId ali brojilo nikad nije očitano
has_meter_no_reads = q("""
    SELECT TOP 1 dt.Id
    FROM DistributionSubstation dt
    WHERE dt.MeterId IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM MeterReads mr WHERE mr.Mid = dt.MeterId)
      AND NOT EXISTS (SELECT 1 FROM MeterReadTfes mt WHERE mt.Mid = dt.MeterId)
""")
silent_dt_id = int(has_meter_no_reads.iloc[0]["Id"]) if not has_meter_no_reads.empty else None
print(f"Brojilo bez rds: {silent_dt_id}")

# 6. DT sa samo kWh podacima (ima Tfes, nema V/I u poslednjih 24h)
only_kwh = q("""
    WITH meter_last AS (SELECT Mid, MAX(Ts) AS last_ts FROM MeterReadTfes GROUP BY Mid),
         has_tfes AS (
            SELECT mt.Mid, COUNT(*) AS cnt FROM MeterReadTfes mt
            JOIN meter_last ml ON mt.Mid = ml.Mid
            WHERE mt.Ts > DATEADD(HOUR, -24, ml.last_ts)
            GROUP BY mt.Mid
         ),
         has_reads AS (
            SELECT mr.Mid, COUNT(*) AS cnt FROM MeterReads mr
            JOIN meter_last ml ON mr.Mid = ml.Mid
            WHERE mr.Ts > DATEADD(HOUR, -24, ml.last_ts)
            GROUP BY mr.Mid
         )
    SELECT TOP 1 dt.Id
    FROM DistributionSubstation dt
    JOIN has_tfes t ON dt.MeterId = t.Mid
    LEFT JOIN has_reads r ON dt.MeterId = r.Mid
    WHERE r.cnt IS NULL OR r.cnt = 0
""")
only_kwh_dt_id = int(only_kwh.iloc[0]["Id"]) if not only_kwh.empty else None
print(f"Samo kWh:        {only_kwh_dt_id}")


# ─────────────────────────────────────────────
# SCENARIJI
# ─────────────────────────────────────────────

results = []

section("SCENARIJI")

if best_dt_id:
    results.append(test_dt(best_dt_id, "1. Najviše merenja (idealan)",
                           "puna animacija sa 48+ frame-ova"))

if mid_dt_id:
    results.append(test_dt(mid_dt_id, "2. Srednja pokrivenost",
                           "vidljivi gapovi, manje frame-ova"))

if worst_dt_id:
    results.append(test_dt(worst_dt_id, "3. Malo merenja (1-5)",
                           "graf ne puca, pokazuje retke tačke"))

if no_meter_dt_id:
    results.append(test_dt(no_meter_dt_id, "4. DT bez MeterId",
                           "prazan graf sa porukom 'Nema merenja'"))

if silent_dt_id:
    results.append(test_dt(silent_dt_id, "5. DT sa brojilom ali bez očitavanja",
                           "prazan graf sa porukom"))

results.append(test_dt(999_999_999, "6. Nepostojeći DT (id=999999999)",
                       "prazan graf sa porukom"))

if only_kwh_dt_id:
    results.append(test_dt(only_kwh_dt_id, "7. Samo kWh podaci (nema V/I)",
                           "napon+struja prazno, kwh pravi vrednosti"))

results.append(test_dt(38110, "8. Tvoj problematični DT (16 7 SF BATALLION)",
                       "outlier-i skriveni, gap-ovi vidljivi"))


# ─────────────────────────────────────────────
# REZIME
# ─────────────────────────────────────────────

section("REZIME")
uspeh = sum(1 for ok, _ in results if ok)
print(f"Prošlo:  {uspeh}/{len(results)}")
print(f"Palo:    {len(results) - uspeh}/{len(results)}")

failures = [(i, err) for i, (ok, err) in enumerate(results) if not ok]
if failures:
    print("\nPali testovi:")
    for i, err in failures:
        print(f"  #{i+1}: {err}")
    sys.exit(1)
else:
    print("\n✅ Svi edge case-ovi prošli!")