"""
graphs/plot_dt.py

Robusni animirani graf napona, struje i potrošnje (kWh) jedne DT.

Pokretanje (iz root foldera):
    python graphs/plot_dt.py            # najbolji DT automatski
    python graphs/plot_dt.py 335
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "get_data"))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fetch_dt import get_dt_readings_24h, get_dt_info, list_active_dts

SCALE = 100.0
V_MIN, V_MAX = 50.0, 300.0
I_MIN, I_MAX = 0.0, 2000.0
MAX_GAP_MINUTES = 120

BOJA_V = "#378ADD"   # plava — napon
BOJA_I = "#EF9F27"   # narandzasta — struja
BOJA_E = "#1D9E75"   # zelena — energija


# ─────────────────────────────────────────────
# PRIPREMA
# ─────────────────────────────────────────────

def pripremi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Raw → fizičke jedinice + outlier filter + agregati po fazama.

    Rezultat sadrži:
        Ts
        v_avg     — prosek napona 3 faze (V)
        i_sum     — zbir struja 3 faze (A), ukupno opterećenje trafoa
        kwh_raw   — kumulativna vrednost (može biti NaN)
        kwh_delta — potrošnja u intervalu (kWh u tom polu-satu)
    """
    d = df.copy()
    d["Ts"] = pd.to_datetime(d["Ts"])
    d = d.sort_values("Ts").reset_index(drop=True)

    # Skaliranje i outlier filter po fazi
    for ph in ("a", "b", "c"):
        v = d[f"V_{ph}"].astype(float) / SCALE
        i = d[f"I_{ph}"].astype(float) / SCALE
        v = v.where((v >= V_MIN) & (v <= V_MAX))
        i = i.where((i >= I_MIN) & (i <= I_MAX))
        d[f"_v_{ph}"] = v
        d[f"_i_{ph}"] = i

    # Napon = prosek validnih faza (ignoriše NaN)
    d["v_avg"] = d[["_v_a", "_v_b", "_v_c"]].mean(axis=1, skipna=True)

    # Struja = suma faza (ukupno opterećenje trafoa)
    # Ako su sve tri NaN → ostaje NaN
    all_nan_i = d[["_i_a", "_i_b", "_i_c"]].isna().all(axis=1)
    d["i_sum"] = d[["_i_a", "_i_b", "_i_c"]].sum(axis=1, skipna=True)
    d.loc[all_nan_i, "i_sum"] = np.nan

    # kWh raw + delta (potrošnja u intervalu)
    d["kwh_raw"] = d["kwh"] if "kwh" in d.columns else np.nan
    d["kwh_delta"] = d["kwh_raw"].diff()
    # prvi red nema prethodnika → NaN je ok
    # negativne razlike (reset brojila) → NaN
    d.loc[d["kwh_delta"] < 0, "kwh_delta"] = np.nan

    # gap detection
    gap = d["Ts"].diff().dt.total_seconds() / 60
    d["is_gap"] = (gap > MAX_GAP_MINUTES).fillna(False)

    return d[["Ts", "v_avg", "i_sum", "kwh_raw", "kwh_delta", "is_gap"]]


def insert_gaps(d: pd.DataFrame, col: str) -> tuple[list, list]:
    """Umetni NaN u liniju pre svake tačke koja je 'preko gap-a'."""
    xs, ys = [], []
    for _, row in d.iterrows():
        if row["is_gap"]:
            xs.append(row["Ts"])
            ys.append(np.nan)
        xs.append(row["Ts"])
        ys.append(row[col])
    return xs, ys


# ─────────────────────────────────────────────
# KVALITET PODATAKA (banner)
# ─────────────────────────────────────────────

def kvalitet_podataka(d: pd.DataFrame) -> dict:
    n = len(d)
    if n == 0:
        return {"ukupno": 0, "sati": 0, "valid_v": 0, "valid_i": 0, "valid_e": 0}
    raspon = (d["Ts"].max() - d["Ts"].min()).total_seconds() / 3600 if n > 1 else 0
    return {
        "ukupno": n,
        "sati": round(raspon, 1),
        "valid_v": int(d["v_avg"].notna().sum()),
        "valid_i": int(d["i_sum"].notna().sum()),
        "valid_e": int(d["kwh_delta"].notna().sum()),
    }


# ─────────────────────────────────────────────
# ANIMACIJA — FRAME-OVI
# ─────────────────────────────────────────────

def _build_frames(d: pd.DataFrame) -> list:
    """
    Po jedan frame za svaki timestamp. Graf se 'crta' postepeno.
    """
    frames = []
    n = len(d)
    for k in range(1, n + 1):
        sub = d.iloc[:k]
        v_x, v_y = insert_gaps(sub, "v_avg")
        i_x, i_y = insert_gaps(sub, "i_sum")
        e_x, e_y = insert_gaps(sub, "kwh_delta")
        frames.append(go.Frame(
            name=str(k),
            data=[
                go.Scatter(x=v_x, y=v_y),
                go.Scatter(x=i_x, y=i_y),
                go.Scatter(x=e_x, y=e_y),
            ],
            traces=[0, 1, 2],
        ))
    return frames


# ─────────────────────────────────────────────
# CRTANJE
# ─────────────────────────────────────────────

def nacrtaj(dt_id: int) -> go.Figure:
    df   = get_dt_readings_24h(dt_id)
    info = get_dt_info(dt_id)
    naziv = info["name"] if info else f"DT {dt_id}"

    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"<b>{naziv}</b><br>Nema merenja za ovu stanicu.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="#888"),
        )
        fig.update_layout(height=400, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    d = pripremi(df)
    k = kvalitet_podataka(d)

    banner = (
        f"<sup><i>"
        f"{k['ukupno']} merenja · "
        f"{k['sati']}h pokriveno · "
        f"V:{k['valid_v']} I:{k['valid_i']} E:{k['valid_e']}"
        f"</i></sup>"
    )
    naslov = f"<b>{naziv}</b> — poslednja 24h<br>{banner}"

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            "Prosečan napon 3 faze (V)",
            "Ukupna struja kroz trafo (A)",
            "Potrošnja u intervalu (kWh)",
        ),
    )

    hover = "%{x|%d.%m %H:%M}"

    # Početni (prazni) trace-ovi — biće popunjeni u frame-ovima
    # Red 1 — Napon
    v_x, v_y = insert_gaps(d, "v_avg")
    fig.add_trace(go.Scatter(
        x=v_x, y=v_y, name="Napon (prosek)",
        mode="lines+markers",
        line=dict(color=BOJA_V, width=2.5),
        marker=dict(size=6, color=BOJA_V),
        connectgaps=False,
        hovertemplate=f"<b>Napon</b>: %{{y:.1f}} V<br>{hover}<extra></extra>",
    ), row=1, col=1)

    # Red 2 — Struja
    i_x, i_y = insert_gaps(d, "i_sum")
    fig.add_trace(go.Scatter(
        x=i_x, y=i_y, name="Struja (ukupno)",
        mode="lines+markers",
        line=dict(color=BOJA_I, width=2.5),
        marker=dict(size=6, color=BOJA_I),
        connectgaps=False,
        hovertemplate=f"<b>Struja</b>: %{{y:.2f}} A<br>{hover}<extra></extra>",
    ), row=2, col=1)

    # Red 3 — Potrošnja u intervalu (kWh delta)
    e_x, e_y = insert_gaps(d, "kwh_delta")
    fig.add_trace(go.Scatter(
        x=e_x, y=e_y, name="Potrošnja (kWh)",
        mode="lines+markers",
        line=dict(color=BOJA_E, width=2.5),
        marker=dict(size=6, color=BOJA_E),
        connectgaps=False,
        fill="tozeroy",
        fillcolor="rgba(29, 158, 117, 0.12)",
        hovertemplate=f"<b>Potrošeno</b>: %{{y:.2f}} kWh<br>{hover}<extra></extra>",
    ), row=3, col=1)

    # Frame-ovi za animaciju
    fig.frames = _build_frames(d)

    # Play / Pause + slider
    n = len(d)
    fig.update_layout(
        updatemenus=[dict(
            type="buttons", direction="left",
            x=0, y=1.14, xanchor="left", yanchor="top",
            pad=dict(t=0, r=10),
            showactive=False,
            buttons=[
                dict(label="▶ Play", method="animate",
                    args=[None, dict(
                        frame=dict(duration=80, redraw=True),
                        fromcurrent=True, mode="immediate",
                        transition=dict(duration=0))]),
                dict(label="⏩ Fast", method="animate",
                    args=[None, dict(
                        frame=dict(duration=20, redraw=True),
                        fromcurrent=True, mode="immediate",
                        transition=dict(duration=0))]),
                dict(label="⏸ Pause", method="animate",
                    args=[[None], dict(
                        frame=dict(duration=0, redraw=False),
                        mode="immediate",
                        transition=dict(duration=0))]),
            ],
        )],
        sliders=[dict(
            active=n - 1,  # počni sa punim grafom
            x=0.1, y=-0.02, len=0.9,
            currentvalue=dict(prefix="Trenutak: ", font=dict(size=12)),
            pad=dict(t=30, b=10),
            steps=[dict(
                method="animate",
                label=d.iloc[i - 1]["Ts"].strftime("%d.%m %H:%M"),
                args=[[str(i)], dict(
                    mode="immediate",
                    frame=dict(duration=0, redraw=True),
                    transition=dict(duration=0))],
            ) for i in range(1, n + 1)],
        )],
    )

    # Fiksni opsezi (da se animacija ne "skače")
    grid = "rgba(0,0,0,0.07)"
    fig.update_yaxes(title_text="Napon (V)", gridcolor=grid,
                     range=[V_MIN, V_MAX], row=1, col=1)
    fig.update_yaxes(title_text="Struja (A)", gridcolor=grid,
                     rangemode="tozero", row=2, col=1)
    fig.update_yaxes(title_text="kWh", gridcolor=grid,
                     rangemode="tozero", row=3, col=1)
    fig.update_xaxes(gridcolor=grid,
                     range=[d["Ts"].min(), d["Ts"].max()])
    fig.update_xaxes(title_text="Vreme", row=3, col=1)

    # Nameplate
    if info and info.get("nameplate_kva"):
        fig.add_hline(
            y=info["nameplate_kva"],
            row=3, col=1,
            line=dict(color="rgba(180,30,30,0.5)", width=1.5, dash="dash"),
            annotation_text=f"Nameplate {info['nameplate_kva']} kVA",
            annotation_position="top right",
        )

    fig.update_layout(
        title=dict(text=naslov, font=dict(size=15)),
        hovermode="x unified",
        height=900,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=70, r=30, t=130, b=90),
        legend=dict(orientation="h", y=1.08, x=0.15),
    )

    return fig


# ─────────────────────────────────────────────
# POKRETANJE
# ─────────────────────────────────────────────

def _nadji_najbolji_dt() -> int:
    from db import q
    best = q("""
        WITH meter_last AS (
            SELECT Mid, MAX(Ts) AS last_ts FROM MeterReads GROUP BY Mid
        ),
        counts AS (
            SELECT mr.Mid, COUNT(*) AS cnt
            FROM MeterReads mr
            JOIN meter_last ml ON mr.Mid = ml.Mid
            WHERE mr.Ts > DATEADD(HOUR, -24, ml.last_ts)
            GROUP BY mr.Mid
        )
        SELECT TOP 1 dt.Id, dt.Name, c.cnt
        FROM DistributionSubstation dt
        JOIN counts c ON dt.MeterId = c.Mid
        ORDER BY c.cnt DESC
    """)
    if best.empty:
        return int(list_active_dts().iloc[0]["id"])
    print(f"(default) najbolji DT: {best.iloc[0]['Id']} "
          f"'{best.iloc[0]['Name']}' — {best.iloc[0]['cnt']} merenja")
    return int(best.iloc[0]["Id"])


if __name__ == "__main__":
    dt_id = int(sys.argv[1]) if len(sys.argv) > 1 else _nadji_najbolji_dt()

    info = get_dt_info(dt_id)
    if info is None:
        print(f"Nema DT-a sa id={dt_id}")
        sys.exit(1)

    df = get_dt_readings_24h(dt_id)
    print(f"\nDT:          {info['name']}  (id={dt_id})")
    if df is not None:
        d = pripremi(df)
        k = kvalitet_podataka(d)
        print(f"Očitavanja:  {k['ukupno']}")
        print(f"Validnih:    V={k['valid_v']}, I={k['valid_i']}, E={k['valid_e']}")

    fig = nacrtaj(dt_id)
    out_path = os.path.join(os.path.dirname(__file__), "dt_graf.html")
    fig.write_html(out_path)
    print(f"\nGrafik: {out_path}")
    print("Klikni ▶ Play da pokreneš animaciju.\n")