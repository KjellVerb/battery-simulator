"""Streamlit-interface voor de Vlaamse thuisbatterij-simulator."""

from __future__ import annotations

import hashlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from load_fluvius import load_quarter_hour_csv
from presets import BATTERY_PRESETS, CAPACITY_TARIFFS_EUR_PER_KW_YEAR
from simulate import BatteryParams, TariffParams, summarise, simulate_battery

README_CSV_INSTRUCTIES = (
    "https://github.com/KjellVerb/battery-simulator#csv-export"
)

PARAM_KEYS = (
    "capacity_kwh",
    "charge_efficiency",
    "discharge_efficiency",
    "max_charge_kw",
    "max_discharge_kw",
    "min_soc_pct",
    "cost_eur",
    "lifetime_years",
    "self_discharge_pct_per_day",
)

STRATEGY_UI_TO_INTERNAL = {
    "Eigen verbruik": "Self-consumption",
    "Piekafvlakking": "Peak shaving",
    "Hybride": "Hybrid",
}

RESOLUTION_UI_TO_PANDAS = {
    "15 minuten": "15 min",
    "Uur": "h",
    "Dag": "D",
}


def _init_state() -> None:
    defaults = BATTERY_PRESETS["Tesla Powerwall 3 (13.5 kWh)"]
    st.session_state.setdefault("preset", "Tesla Powerwall 3 (13.5 kWh)")
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _on_preset_change() -> None:
    preset = BATTERY_PRESETS.get(st.session_state.preset)
    if not preset:
        return
    for key, value in preset.items():
        st.session_state[key] = value


@st.cache_data(show_spinner="Fluvius CSV laden…")
def _cached_load(csv_bytes: bytes, digest: str) -> pd.DataFrame:
    del digest  # cache key only
    return load_quarter_hour_csv(csv_bytes)


def _store_upload(uploaded) -> None:
    payload = uploaded.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    if st.session_state.get("csv_digest") == digest:
        return
    st.session_state["csv_bytes"] = payload
    st.session_state["csv_name"] = uploaded.name
    st.session_state["csv_digest"] = digest
    for key in ("last_summary", "last_sim"):
        st.session_state.pop(key, None)


def _comparison_table(summary: dict) -> pd.DataFrame:
    wout, with_b, delta = summary["without"], summary["with"], summary["delta"]
    rows = [
        ("Totale afname van het net", "kWh", "consumption_kwh"),
        ("Totale injectie", "kWh", "injection_kwh"),
        ("Energiekost", "€", "energy_cost_eur"),
        ("Kwartierpiek / capaciteitstarief", "€", "peak_cost_eur"),
        ("Totale kost", "€", "total_cost_eur"),
    ]
    records = []
    for label, unit, key in rows:
        records.append(
            {
                "Gegeven": f"{label} ({unit})",
                "Zonder batterij": wout[key],
                "Met batterij": with_b[key],
                "Verschil": delta[key],
            }
        )
    records.append(
        {
            "Gegeven": "Gemiddelde gefactureerde maandpiek (kW)",
            "Zonder batterij": wout["avg_monthly_peak_kw"],
            "Met batterij": with_b["avg_monthly_peak_kw"],
            "Verschil": with_b["avg_monthly_peak_kw"] - wout["avg_monthly_peak_kw"],
        }
    )
    records.append(
        {
            "Gegeven": "Terugverdientijd investering batterij",
            "Zonder batterij": "—",
            "Met batterij": summary["payback_label"],
            "Verschil": summary["savings_per_year_eur"],
        }
    )
    return pd.DataFrame(records)


def _format_comparison(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    def fmt(value, metric: str):
        if isinstance(value, str):
            return value
        if "Terugverdientijd" in metric:
            return f"{value:,.0f} €/jaar besparing"
        if "€" in metric or "kost" in metric.lower() or "Totale kost" in metric:
            return f"{value:,.2f}"
        return f"{value:,.1f}"

    for col in ("Zonder batterij", "Met batterij", "Verschil"):
        out[col] = [fmt(v, m) for v, m in zip(out[col], out["Gegeven"])]
    return out


def _downsample(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == "15 min":
        return frame
    energy_cols = [
        "offtake_kwh",
        "injection_kwh",
        "grid_import_kwh",
        "grid_export_kwh",
        "charge_kwh",
        "discharge_kwh",
    ]
    agg = {c: "sum" for c in energy_cols if c in frame.columns}
    agg["soc_kwh"] = "mean"
    agg["grid_import_kw"] = "mean"
    agg["baseline_import_kw"] = "mean"
    return frame.resample(rule).agg(agg).dropna(how="all")


def _build_figure(sim: pd.DataFrame, resolution: str) -> go.Figure:
    plot = _downsample(sim, resolution)
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=(
            "Laadstatus batterij (SOC)",
            "Netafname vermogen (kwartierpiek)",
            "Energiestromen",
        ),
        specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]],
    )
    fig.add_trace(
        go.Scattergl(
            x=plot.index,
            y=plot["soc_kwh"],
            name="SOC",
            line=dict(color="#2563eb", width=1.4),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=plot.index,
            y=plot["baseline_import_kw"],
            name="Afname zonder batterij",
            line=dict(color="#94a3b8", width=1),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=plot.index,
            y=plot["grid_import_kw"],
            name="Afname met batterij",
            line=dict(color="#dc2626", width=1.2),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=plot.index,
            y=plot["charge_kwh"] * 4.0,
            name="Batterij laden",
            line=dict(color="#16a34a", width=1),
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=plot.index,
            y=plot["discharge_kwh"] * 4.0,
            name="Batterij ontladen",
            line=dict(color="#d97706", width=1),
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=plot.index,
            y=plot["grid_export_kwh"] * 4.0,
            name="Injectie met batterij",
            line=dict(color="#7c3aed", width=1),
        ),
        row=3,
        col=1,
    )
    fig.update_yaxes(title_text="kWh", row=1, col=1)
    fig.update_yaxes(title_text="kW", row=2, col=1)
    fig.update_yaxes(title_text="kW", row=3, col=1)
    fig.update_layout(
        height=860,
        legend=dict(orientation="h", yanchor="bottom", y=1.08, x=0),
        margin=dict(t=80, b=40),
        hovermode="x unified",
    )
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1d", step="day", stepmode="backward"),
                dict(count=7, label="7d", step="day", stepmode="backward"),
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(step="all", label="Alles"),
            ]
        ),
        row=3,
        col=1,
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="Thuisbatterij-simulator", layout="wide")
    _init_state()
    st.title("Thuisbatterij – inschatting winst of verlies")
    st.markdown(
        "Deze app helpt inschatten **wat een thuisbatterij je financieel zou kunnen opleveren** "
        "(of kosten), op basis van **jouw historische verbruik** uit Mijn Fluvius. "
        "De simulatie doet alsof de gekozen batterij **in diezelfde periode** al aanwezig was geweest: "
        "kwartier per kwartier wordt berekend hoeveel je van het net zou afnemen en injecteren, "
        "en wat dat zou betekenen voor energiekost, kwartierpiek en terugverdientijd. "
        "Het is **geen voorspelling van de toekomst**, wel een indicatie afgeleid uit het verleden."
    )
    with st.expander("Limitaties en aannames"):
        st.markdown(
            """
- **Historiek ≠ toekomst:** je verbruik, zonnepanelen, gezin en tarieven kunnen veranderen; resultaten zijn indicatief.
- **Vaste gemiddelde prijzen:** afname en teruglevering gebruiken één €/kWh die jij invult; geen dynamische prijzen, geen day-ahead, geen onbalans of cap-tarief op energie.
- **Geen prijsprognose:** de app heeft geen zicht op toekomstige stroomprijzen, prosumententarief of regelgeving.
- **Resolutie 15 minuten:** Fluvius-kwartiertotalen; pieken binnen een kwartier worden niet gemodelleerd.
- **Vereenvoudigde batterijsturing:** laden uit injectie, ontladen volgens gekozen strategie; geen omvormerlimieten van je installatie, geen netregels of exportbeperkingen.
- **Capaciteitstarief (Vlaanderen):** gemiddelde maandpiek op netafname, minimum 2,5 kW; geen volledige netfactuur (kWh-tarief net, databeheer, maximaaltarief, …).
- **Presetkosten:** investering en levensduur zijn richtwaarden; geen onderhoud, verzekering, rendement of restwaarde.
- **Privacy:** upload blijft in je sessie; er worden geen bestanden op de server bewaard.
            """
        )

    with st.sidebar:
        st.header("Gegevens")
        uploaded = st.file_uploader(
            "Fluvius CSV",
            type=["csv"],
            help="Export met detailniveau Kwartiertotalen uit Mijn Fluvius.",
        )
        if uploaded is not None:
            _store_upload(uploaded)
        st.markdown(
            f"[Instructies: CSV exporteren via Mijn Fluvius]({README_CSV_INSTRUCTIES})"
        )

        st.header("Elektriciteitsprijzen")
        import_price = st.number_input(
            "Gemiddelde stroomprijs (€/kWh)",
            min_value=0.0,
            value=0.32,
            step=0.01,
            format="%.3f",
            help="All-in aankoopprijs voor netafname.",
        )
        export_price = st.number_input(
            "Terugleververgoeding (€/kWh)",
            min_value=0.0,
            value=0.04,
            step=0.01,
            format="%.3f",
            help="Vergoeding of verrekening voor kWh die je injecteert.",
        )

        st.header("Kwartierpiek (capaciteitstarief)")
        dso_names = list(CAPACITY_TARIFFS_EUR_PER_KW_YEAR) + ["Aangepast"]
        default_dso = (
            "Vlaams gemiddelde"
            if "Vlaams gemiddelde" in dso_names
            else dso_names[0]
        )
        dso = st.selectbox("Netbeheerzone", dso_names, index=dso_names.index(default_dso))
        if dso == "Aangepast":
            capacity_rate = st.number_input(
                "Capaciteitstarief (€/kW/jaar, incl. btw)",
                min_value=0.0,
                value=56.59,
                step=0.1,
            )
        else:
            capacity_rate = CAPACITY_TARIFFS_EUR_PER_KW_YEAR[dso]
            st.caption(f"Tarief {capacity_rate:.2f} €/kW/jaar (2026, incl. 6% btw).")

        st.header("Batterij")
        st.selectbox(
            "Preset",
            list(BATTERY_PRESETS),
            key="preset",
            on_change=_on_preset_change,
        )
        st.number_input("Opslagcapaciteit (kWh)", min_value=0.1, step=0.1, key="capacity_kwh")
        st.number_input(
            "Laadefficiëntie",
            min_value=0.1,
            max_value=1.0,
            step=0.01,
            format="%.3f",
            key="charge_efficiency",
        )
        st.number_input(
            "Ontlaadefficiëntie",
            min_value=0.1,
            max_value=1.0,
            step=0.01,
            format="%.3f",
            key="discharge_efficiency",
        )
        st.number_input("Max. laadvermogen (kW)", min_value=0.1, step=0.1, key="max_charge_kw")
        st.number_input("Max. ontlaadvermogen (kW)", min_value=0.1, step=0.1, key="max_discharge_kw")
        st.number_input(
            "Minimum laadniveau / max. ontlaadniveau (%)",
            min_value=0.0,
            max_value=50.0,
            step=1.0,
            key="min_soc_pct",
            help="Ondergrens SOC. 10% betekent dat de batterij nooit onder 10% van de capaciteit gaat.",
        )
        st.number_input("Investeringskost (€)", min_value=0.0, step=100.0, key="cost_eur")
        st.number_input("Verwachte levensduur (jaar)", min_value=1.0, step=1.0, key="lifetime_years")
        st.number_input(
            "Zelfontlading (% per dag)",
            min_value=0.0,
            max_value=5.0,
            step=0.01,
            format="%.3f",
            key="self_discharge_pct_per_day",
        )
        st.caption(
            "Een preset overschrijft de velden. Kies **Aangepast** of pas waarden aan na selectie. "
            "Prijzen zijn indicatieve totaalprijzen incl. installatie."
        )

        st.header("Aansturing")
        strategy_ui = st.selectbox(
            "Regelstrategie",
            tuple(STRATEGY_UI_TO_INTERNAL),
            help=(
                "Eigen verbruik: ontladen zoveel mogelijk bij afname. "
                "Piekafvlakking: ontladen enkel boven het streefvermogen. "
                "Hybride: gereserveerd SOC voor pieken, rest voor eigen verbruik."
            ),
        )
        peak_target = st.number_input(
            "Streefvermogen piekafvlakking (kW)",
            min_value=0.0,
            value=2.5,
            step=0.1,
            help="Minimum gefactureerde piek is 2,5 kW; daaronder verlaag je het capaciteitstarief niet.",
        )
        reserve_pct = st.slider(
            "Gereserveerd SOC voor pieken (%)",
            min_value=0,
            max_value=80,
            value=30,
            disabled=strategy_ui != "Hybride",
        )
        resolution_ui = st.selectbox(
            "Grafiekresolutie",
            tuple(RESOLUTION_UI_TO_PANDAS),
            index=1,
        )
        resolution = RESOLUTION_UI_TO_PANDAS[resolution_ui]

        run = st.button("Simulatie uitvoeren", type="primary", use_container_width=True)

    csv_bytes = st.session_state.get("csv_bytes")
    if not csv_bytes:
        st.info("Upload een Fluvius CSV (kwartiertotalen) om te starten.")
        return

    digest = st.session_state.get("csv_digest", "")
    csv_name = st.session_state.get("csv_name", "upload.csv")
    try:
        data = _cached_load(csv_bytes, digest)
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error(
            "Dit bestand kon niet worden gelezen. Controleer of het een Fluvius-export "
            "met kwartiertotalen is (kolommen Register, Volume, Van (datum))."
        )
        return

    st.write(
        f"Bestand **{csv_name}**: **{len(data):,}** kwartieren "
        f"({data.index.min():%Y-%m-%d %H:%M} tot {data.index.max():%Y-%m-%d %H:%M})."
    )

    if not run and "last_summary" not in st.session_state:
        st.info("Stel de parameters in en klik op **Simulatie uitvoeren**.")
        return

    if run:
        battery = BatteryParams(**{k: float(st.session_state[k]) for k in PARAM_KEYS})
        tariff = TariffParams(
            import_eur_per_kwh=float(import_price),
            export_eur_per_kwh=float(export_price),
            capacity_eur_per_kw_year=float(capacity_rate),
        )
        strategy = STRATEGY_UI_TO_INTERNAL[strategy_ui]
        with st.spinner("Simulatie bezig…"):
            sim = simulate_battery(data, battery, strategy, float(peak_target), float(reserve_pct))
            summary = summarise(data, sim, battery, tariff)
        st.session_state.last_sim = sim
        st.session_state.last_summary = summary

    summary = st.session_state.last_summary
    sim = st.session_state.last_sim
    years = summary["period_years"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Periode", f"{years:.2f} jaar")
    c2.metric("Besparing / jaar", f"{summary['savings_per_year_eur']:,.0f} €")
    c3.metric("Terugverdientijd", summary["payback_label"])
    c4.metric("Netto over levensduur", f"{summary['lifetime_net_eur']:,.0f} €")

    st.subheader("Vergelijking zonder / met batterij")
    st.caption(
        f"Totalen over de volledige dataset ({years:.2f} jaar), "
        "niet geannualiseerd behalve terugverdientijd."
    )
    table = _comparison_table(summary)
    st.dataframe(_format_comparison(table), use_container_width=True, hide_index=True)

    peaks = pd.DataFrame(
        {
            "Maandpiek zonder batterij (kW)": summary["baseline_monthly_peaks"],
            "Maandpiek met batterij (kW)": summary["battery_monthly_peaks"],
        }
    )
    with st.expander("Maandelijkse kwartierpieken"):
        st.dataframe(peaks.round(2), use_container_width=True)

    st.subheader("Tijdreeks")
    st.plotly_chart(_build_figure(sim, resolution), use_container_width=True)
    st.caption(
        "Zoom met scroll/pinch, de rangeslider of de knoppen 1d/7d/1m. "
        "Kwartierpiek = gemiddeld afnamevermogen over 15 min (kWh in het interval × 4)."
    )


if __name__ == "__main__":
    main()
