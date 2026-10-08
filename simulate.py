"""Home-battery dispatch and Flanders capacity-tariff costing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from presets import MIN_BILLED_PEAK_KW

DT_H = 0.25


@dataclass(frozen=True)
class BatteryParams:
    capacity_kwh: float
    charge_efficiency: float
    discharge_efficiency: float
    max_charge_kw: float
    max_discharge_kw: float
    min_soc_pct: float
    cost_eur: float
    lifetime_years: float
    self_discharge_pct_per_day: float = 0.0


@dataclass(frozen=True)
class TariffParams:
    import_eur_per_kwh: float
    export_eur_per_kwh: float
    capacity_eur_per_kw_year: float
    min_billed_peak_kw: float = MIN_BILLED_PEAK_KW


def _monthly_peaks_kw(index: pd.DatetimeIndex, offtake_kwh: np.ndarray) -> pd.Series:
    power = pd.Series(offtake_kwh * 4.0, index=index)
    return power.resample("ME").max()


def capacity_cost_eur(
    index: pd.DatetimeIndex,
    offtake_kwh: np.ndarray,
    tariff: TariffParams,
    period_years: float,
) -> tuple[float, float, pd.Series]:
    peaks = _monthly_peaks_kw(index, offtake_kwh).dropna()
    if peaks.empty:
        return 0.0, tariff.min_billed_peak_kw, peaks
    avg_peak = float(peaks.mean())
    billed = max(avg_peak, tariff.min_billed_peak_kw)
    return billed * tariff.capacity_eur_per_kw_year * period_years, billed, peaks


def simulate_battery(
    data: pd.DataFrame,
    battery: BatteryParams,
    strategy: str,
    peak_target_kw: float,
    reserve_pct: float,
) -> pd.DataFrame:
    """Charge from surplus injection; discharge according to strategy.

    Strategies:
    - Self-consumption: cover as much offtake as possible.
    - Peak shaving: discharge only when offtake power would exceed the target.
    - Hybrid: self-consumption using SOC above the reserve; reserved energy
      is used only to keep offtake at or below the peak target.
    """
    offtake = data["offtake_kwh"].to_numpy(dtype=np.float64)
    injection = data["injection_kwh"].to_numpy(dtype=np.float64)
    n = offtake.size

    soc_min = battery.capacity_kwh * (battery.min_soc_pct / 100.0)
    soc_max = battery.capacity_kwh
    reserve_floor = max(soc_min, soc_max * (reserve_pct / 100.0))
    eta_c = min(max(battery.charge_efficiency, 1e-6), 1.0)
    eta_d = min(max(battery.discharge_efficiency, 1e-6), 1.0)
    max_charge_ac = battery.max_charge_kw * DT_H
    max_discharge_ac = battery.max_discharge_kw * DT_H
    peak_energy = peak_target_kw * DT_H
    leak = (battery.self_discharge_pct_per_day / 100.0) * (DT_H / 24.0)

    soc = np.empty(n, dtype=np.float64)
    grid_in = np.empty(n, dtype=np.float64)
    grid_out = np.empty(n, dtype=np.float64)
    charge_ac = np.empty(n, dtype=np.float64)
    discharge_ac = np.empty(n, dtype=np.float64)

    energy = 0.5 * (soc_min + soc_max)
    hybrid = strategy == "Hybrid"
    peak_only = strategy == "Peak shaving"

    for i in range(n):
        energy *= 1.0 - leak
        energy = min(max(energy, soc_min), soc_max)

        room_ac = (soc_max - energy) / eta_c
        ch = min(injection[i], max_charge_ac, max(room_ac, 0.0))
        energy += ch * eta_c
        surplus = injection[i] - ch

        offt = offtake[i]
        if peak_only:
            want = max(0.0, offt - peak_energy)
            available = (energy - soc_min) * eta_d
        elif hybrid:
            sc_available = max(0.0, energy - reserve_floor) * eta_d
            sc_want = offt
            sc = min(sc_want, max_discharge_ac, sc_available)
            remaining = offt - sc
            extra_want = max(0.0, remaining - peak_energy)
            extra_available = max(0.0, (energy - soc_min) * eta_d - sc)
            want = sc + min(extra_want, extra_available)
            available = (energy - soc_min) * eta_d
        else:
            want = offt
            available = (energy - soc_min) * eta_d

        dch = min(want, max_discharge_ac, max(available, 0.0))
        energy -= dch / eta_d if eta_d else 0.0
        energy = min(max(energy, soc_min), soc_max)

        charge_ac[i] = ch
        discharge_ac[i] = dch
        grid_in[i] = offt - dch
        grid_out[i] = surplus
        soc[i] = energy

    out = pd.DataFrame(
        {
            "offtake_kwh": offtake,
            "injection_kwh": injection,
            "grid_import_kwh": grid_in,
            "grid_export_kwh": grid_out,
            "charge_kwh": charge_ac,
            "discharge_kwh": discharge_ac,
            "soc_kwh": soc,
            "grid_import_kw": grid_in * 4.0,
            "baseline_import_kw": offtake * 4.0,
        },
        index=data.index,
    )
    return out


def summarise(
    data: pd.DataFrame,
    sim: pd.DataFrame,
    battery: BatteryParams,
    tariff: TariffParams,
) -> dict:
    index = data.index
    span = (index[-1] - index[0]) + pd.Timedelta(minutes=15)
    years = max(span / pd.Timedelta(days=365.25), 1e-9)

    base_import = float(data["offtake_kwh"].sum())
    base_export = float(data["injection_kwh"].sum())
    bat_import = float(sim["grid_import_kwh"].sum())
    bat_export = float(sim["grid_export_kwh"].sum())

    base_energy = base_import * tariff.import_eur_per_kwh - base_export * tariff.export_eur_per_kwh
    bat_energy = bat_import * tariff.import_eur_per_kwh - bat_export * tariff.export_eur_per_kwh

    base_cap, base_peak, base_peaks = capacity_cost_eur(
        index, data["offtake_kwh"].to_numpy(), tariff, years
    )
    bat_cap, bat_peak, bat_peaks = capacity_cost_eur(
        index, sim["grid_import_kwh"].to_numpy(), tariff, years
    )

    base_total = base_energy + base_cap
    bat_total = bat_energy + bat_cap
    savings_period = base_total - bat_total
    savings_year = savings_period / years
    if savings_year > 1e-9:
        payback_years = battery.cost_eur / savings_year
        payback_label = f"{payback_years:.1f} jaar"
        if battery.lifetime_years > 0 and payback_years > battery.lifetime_years:
            payback_label += f" (langer dan {battery.lifetime_years:.0f} jaar levensduur)"
    elif savings_year < -1e-9:
        payback_years = float("inf")
        payback_label = "Nooit (batterij verhoogt de kosten)"
    else:
        payback_years = float("inf")
        payback_label = "Nooit (geen besparing)"

    lifetime_net = savings_year * battery.lifetime_years - battery.cost_eur

    return {
        "period_years": years,
        "start": index[0],
        "end": index[-1],
        "without": {
            "consumption_kwh": base_import,
            "injection_kwh": base_export,
            "energy_cost_eur": base_energy,
            "peak_cost_eur": base_cap,
            "total_cost_eur": base_total,
            "avg_monthly_peak_kw": base_peak,
        },
        "with": {
            "consumption_kwh": bat_import,
            "injection_kwh": bat_export,
            "energy_cost_eur": bat_energy,
            "peak_cost_eur": bat_cap,
            "total_cost_eur": bat_total,
            "avg_monthly_peak_kw": bat_peak,
        },
        "delta": {
            "consumption_kwh": bat_import - base_import,
            "injection_kwh": bat_export - base_export,
            "energy_cost_eur": bat_energy - base_energy,
            "peak_cost_eur": bat_cap - base_cap,
            "total_cost_eur": bat_total - base_total,
        },
        "payback_years": payback_years,
        "payback_label": payback_label,
        "savings_per_year_eur": savings_year,
        "lifetime_net_eur": lifetime_net,
        "baseline_monthly_peaks": base_peaks,
        "battery_monthly_peaks": bat_peaks,
    }
