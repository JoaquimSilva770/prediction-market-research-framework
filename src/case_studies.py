"""Economic mappings for the four illustrative case-study designs."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class CaseStudy:
    """Describe how a prediction contract maps to a linked financial series."""

    case_id: str
    case_name: str
    prediction_contract: str
    linked_market: str
    linked_symbol: str
    payoff_structure: str
    signal_multiplier: float
    principal_limitation: str


CASE_STUDIES: tuple[CaseStudy, ...] = (
    CaseStudy(
        case_id="tesla",
        case_name="Tesla terminal-price threshold",
        prediction_contract="Tesla closes above $390 at the end of June 2026",
        linked_market="Tesla equity",
        linked_symbol="TSLA",
        payoff_structure="Terminal threshold",
        signal_multiplier=1.0,
        principal_limitation=(
            "Probability sensitivity changes with strike distance, volatility and time."
        ),
    ),
    CaseStudy(
        case_id="bitcoin",
        case_name="Bitcoin monitored barrier",
        prediction_contract="Bitcoin reaches a new all-time high by 30 September 2026",
        linked_market="Bitcoin spot proxy",
        linked_symbol="BTC-USD",
        payoff_structure="Path-dependent barrier",
        signal_multiplier=1.0,
        principal_limitation=(
            "The contract's venue and high-price rule need not match a spot close proxy."
        ),
    ),
    CaseStudy(
        case_id="crude_oil",
        case_name="Crude-oil monitored barrier",
        prediction_contract="Crude oil reaches a new all-time high by 30 September 2026",
        linked_market="Crude-oil futures proxy",
        linked_symbol="CL=F",
        payoff_structure="Discretely monitored barrier",
        signal_multiplier=1.0,
        principal_limitation=(
            "Vendor, active-contract, roll and high-versus-close differences remain."
        ),
    ),
    CaseStudy(
        case_id="federal_reserve",
        case_name="Federal Reserve policy decision",
        prediction_contract="The Fed raises rates by 25 bps at the September 2026 meeting",
        linked_market="Two-year Treasury futures proxy",
        linked_symbol="ZT=F",
        payoff_structure="Indirect policy proxy",
        signal_multiplier=-1.0,
        principal_limitation=(
            "Treasury futures reflect the expected policy path and other macro news."
        ),
    ),
)

CASE_STUDY_BY_ID = {case.case_id: case for case in CASE_STUDIES}


def case_study_table() -> pd.DataFrame:
    """Return the four economic mappings as a readable table."""

    return pd.DataFrame([asdict(case) for case in CASE_STUDIES])
