"""Load Fluvius quarter-hour offtake/injection CSV exports."""

from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import pandas as pd

REGISTER_OFFTAKE = ("Afname Dag", "Afname Nacht")
REGISTER_INJECTION = ("Injectie Dag", "Injectie Nacht")


def _parse_fluvius_raw(raw: pd.DataFrame) -> pd.DataFrame:
    volume = pd.to_numeric(raw["Volume"].str.replace(",", ".", regex=False), errors="coerce")
    ts = pd.to_datetime(
        raw["Van (datum)"] + " " + raw["Van (tijdstip)"],
        format="%d-%m-%Y %H:%M:%S",
        errors="coerce",
    )
    parsed = pd.DataFrame(
        {
            "ts": ts,
            "register": raw["Register"].str.strip(),
            "volume": volume,
        }
    ).dropna(subset=["ts"])

    offtake = (
        parsed.loc[parsed["register"].isin(REGISTER_OFFTAKE)]
        .groupby("ts", sort=True)["volume"]
        .sum()
    )
    injection = (
        parsed.loc[parsed["register"].isin(REGISTER_INJECTION)]
        .groupby("ts", sort=True)["volume"]
        .sum()
    )
    frame = pd.DataFrame({"offtake_kwh": offtake, "injection_kwh": injection}).fillna(0.0)
    if frame.empty:
        raise ValueError("Geen afname of injectie gevonden in het CSV-bestand.")
    full = pd.date_range(frame.index.min(), frame.index.max(), freq="15min")
    frame = frame.reindex(full, fill_value=0.0)
    frame["power_kw"] = frame["offtake_kwh"] * 4.0
    return frame


def load_quarter_hour_csv(source: BinaryIO | bytes) -> pd.DataFrame:
    """Parse Fluvius kwartiertotalen CSV from uploaded bytes or a binary stream."""
    if isinstance(source, bytes):
        source = BytesIO(source)
    raw = pd.read_csv(
        source,
        sep=";",
        dtype=str,
        usecols=["Van (datum)", "Van (tijdstip)", "Register", "Volume"],
    )
    return _parse_fluvius_raw(raw)
