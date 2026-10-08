"""Plug-in presets from https://thuisbatterijgids.net/thuisbatterij/ (prices/RTE, okt 2026)."""

from __future__ import annotations

import math

# (display name, kWh, kW charge/discharge, vanaf-prijs €, RTE % or None → 85%)
_THUISBATTERIJGIDS_ROWS: list[tuple[str, float, float, float, float | None]] = [
    ("HomeWizard Plug-In Battery", 2.7, 0.8, 1195.0, 80.0),
    ("Zendure SolarFlow 2400 AC+", 2.4, 2.4, 819.0, 87.0),
    ("Anker SOLIX Solarbank Max AC", 7.0, 3.5, 1999.0, 85.0),
    ("Zendure SolarFlow 2400 AC", 2.88, 2.4, 969.0, 83.0),
    ("Zendure SolarFlow 2400 AC Pro", 2.4, 2.4, 969.0, 87.0),
    ("Anker SOLIX Solarbank 4 E5000 Pro", 5.0, 2.5, 1799.0, 85.0),
    ("Zendure Hyper 2000", 1.92, 1.0, 978.0, None),
    ("Zendure SolarFlow 800 Pro", 1.92, 0.8, 729.0, None),
    ("Anker SOLIX Solarbank 3 E2700 Pro", 2.69, 1.2, 998.0, 82.0),
    ("Jackery SolarVault 3 Pro", 2.52, 2.5, 789.0, 83.0),
    ("Jackery SolarVault 3 Pro Max", 2.52, 2.5, 1089.0, 83.0),
    ("Jackery SolarVault 3 Pro Max AC", 2.52, 2.5, 764.0, 83.0),
    ("Lunergy X2400 AC", 2.56, 2.4, 1899.0, 85.0),
    ("Marstek Venus E 3.0", 5.12, 2.5, 1148.0, 83.0),
    ("Marstek Venus E 4.0", 5.024, 3.0, 1499.0, None),
    ("Marstek Venus E Mini", 2.0, 1.5, 585.0, 83.0),
    ("Marstek Venus A", 2.12, 1.2, 699.0, 81.0),
    ("Marstek Venus C", 2.56, 2.5, 1099.0, 83.0),
    ("Marstek Venus D", 2.56, 2.2, 1089.0, 83.0),
    ("Marstek Venus E (MPPT)", 5.12, 2.5, 1339.0, 79.0),
    ("EcoFlow Stream AC 5000", 5.02, 3.0, 1499.0, None),
    ("EcoFlow Stream AC Pro", 1.92, 1.2, 649.0, None),
    ("EcoFlow Stream AC", 1.92, 0.8, 599.0, None),
    ("EcoFlow Stream Ultra", 1.92, 1.2, 749.0, None),
    ("EcoFlow Stream Ultra X", 3.0, 1.2, 1098.0, None),
    ("Hyxi Halo", 3.0, 3.0, 1699.0, 81.0),
    ("Hoymiles MS-A2", 2.24, 0.8, 949.0, 92.0),
    ("Lunergy Hub 2400 AC", 5.22, 2.4, 1499.0, 83.0),
    ("Jackery HomePower 2000 Ultra", 2.05, 1.5, 669.0, 83.0),
    ("MOVA LumeGret A4000", 4.0, 2.5, 1349.0, None),
    ("Bluetti Balco 260", 2.56, 1.2, 849.0, 79.0),
    ("Sunpura S2400", 2.4, 2.4, 899.0, 83.0),
    ("Conow Lyra 2500 AC", 2.56, 1.5, 699.0, None),
    ("AEG Solarcube (AS-BBL09)", 4.8, 2.4, 1449.0, 77.0),
    ("Indevolt SolidFlex 2000", 1.79, 2.4, 725.0, None),
    ("Indevolt PowerFlex 2000", 2.0, 2.4, 775.0, 81.0),
    ("Indevolt BK1600", 1.64, 1.2, 399.0, None),
    ("Duravolt Plug-In Battery", 5.12, 2.496, 1400.0, 80.0),
    ("Zinvolt", 1.0, 2.0, 1099.0, 70.0),
    ("TSUNESS PowerTrunk MAU5000", 5.02, 2.5, 1399.0, None),
    ("Voltdeer SR5000 AC Pro", 5.12, 2.5, 1299.0, None),
    ("Zendure SolarFlow 800 Plus", 1.92, 0.8, 479.0, None),
    ("Zendure SolarFlow 800 Pro 2", 1.92, 1.0, 599.0, 82.0),
    ("Zendure SolarFlow 1600 AC+", 1.92, 1.4, 580.0, None),
    ("Zendure SolarFlow 4000 Mix AC+", 8.04, 4.0, 2299.0, 90.0),
    ("Zendure SolarFlow 3000 Mix AC+", 8.04, 3.0, 1745.0, 90.0),
    ("Growatt AURA 5000", 5.02, 2.5, 1160.0, None),
    ("Growatt NEXA 2000", 2.05, 0.8, 675.0, None),
    ("Anker Solix Solarbank 2 E1600 AC", 1.6, 1.2, 599.0, None),
    ("JET GreenArk Pro", 2.6, 2.4, 1200.0, None),
    ("AlphaESS VitaPower 300AC", 4.0, 2.7, 1400.0, None),
    ("Sigenergy SigenMate 2700 Ultra", 2.69, 1.4, 1500.0, None),
    ("NextEnergy thuisbatterij", 2.1, 0.8, 1000.0, None),
    ("ZinVolt Base", 4.0, 0.8, 1200.0, None),
    ("AEG Solarcube Pro", 6.0, 1.5, 1800.0, None),
]


def _row_to_preset(
    name: str,
    kwh: float,
    kw: float,
    cost: float,
    rte_pct: float | None,
) -> dict:
    rte = 0.85 if rte_pct is None else rte_pct / 100.0
    eta = math.sqrt(rte)
    return {
        "capacity_kwh": kwh,
        "charge_efficiency": round(eta, 4),
        "discharge_efficiency": round(eta, 4),
        "max_charge_kw": kw,
        "max_discharge_kw": kw,
        "min_soc_pct": 10.0,
        "cost_eur": cost,
        "lifetime_years": 10.0,
        "self_discharge_pct_per_day": 0.0,
    }


THUISBATTERIJGIDS_PRESETS: dict[str, dict | None] = {
    f"[Gids] {name}": _row_to_preset(name, kwh, kw, cost, rte)
    for name, kwh, kw, cost, rte in _THUISBATTERIJGIDS_ROWS
}
