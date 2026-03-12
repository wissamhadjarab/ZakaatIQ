# zakaatIQ/services/zakat_service.py

from dataclasses import dataclass
from typing import Dict


def clamp_number(value):
    """Safely convert input to float; return 0.0 if invalid."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class ZakatResult:
    assets_total: float
    debts_total: float
    net_zakatable: float
    nisab: float
    is_above_nisab: bool
    zakat_due: float


def calculate_zakat(data: Dict) -> ZakatResult:
    """
    Deterministic Zakat calculation based on classical Islamic finance rules.
    No ML used here — purely rules-based.
    """

    # -----------------------
    # SETTINGS
    # -----------------------
    zakat_rate = clamp_number(data.get("zakat_rate", 0.025))
    nisab_basis = data.get("nisab_basis", "gold")

    gold_price = clamp_number(data.get("gold_price_per_gram", 0))
    silver_price = clamp_number(data.get("silver_price_per_gram", 0))

    nisab_gold_grams = clamp_number(data.get("nisab_gold_grams", 85))
    nisab_silver_grams = clamp_number(data.get("nisab_silver_grams", 595))

    use_metal_weight = data.get("use_metal_weight", False)

    # -----------------------
    # ASSETS
    # -----------------------

    # Cash & Bank
    cash_total = (
        clamp_number(data.get("cash_on_hand")) +
        clamp_number(data.get("bank_accounts"))
    )

    # Gold & Silver
    if use_metal_weight:
        gold_value = clamp_number(data.get("gold_grams")) * gold_price
        silver_value = clamp_number(data.get("silver_grams")) * silver_price
    else:
        gold_value = clamp_number(data.get("gold_value"))
        silver_value = clamp_number(data.get("silver_value"))

    metals_total = gold_value + silver_value

    # Investments
    investments_total = (
        clamp_number(data.get("stocks")) +
        clamp_number(data.get("investments")) +
        clamp_number(data.get("crypto"))
    )

    # Business
    business_total = (
        clamp_number(data.get("business_inventory")) +
        clamp_number(data.get("receivables"))
    )

    # Land (if tradeable / investment property)
    land_total = clamp_number(data.get("land_value"))

    # TOTAL ASSETS
    assets_total = (
        cash_total +
        metals_total +
        investments_total +
        business_total +
        land_total
    )

    # -----------------------
    # DEBTS (short-term only)
    # -----------------------
    debts_total = (
        clamp_number(data.get("short_term_debts")) +
        clamp_number(data.get("bills_taxes_due")) +
        clamp_number(data.get("business_payables"))
    )

    # -----------------------
    # NET ZAKATABLE
    # -----------------------
    net_zakatable = max(assets_total - debts_total, 0)

    # -----------------------
    # NISAB THRESHOLD
    # -----------------------
    if nisab_basis == "gold":
        nisab = gold_price * nisab_gold_grams
    else:
        nisab = silver_price * nisab_silver_grams

    is_above_nisab = net_zakatable >= nisab and nisab > 0

    # -----------------------
    # ZAKAT DUE
    # -----------------------
    zakat_due = net_zakatable * zakat_rate if is_above_nisab else 0

    return ZakatResult(
        assets_total=round(assets_total, 2),
        debts_total=round(debts_total, 2),
        net_zakatable=round(net_zakatable, 2),
        nisab=round(nisab, 2),
        is_above_nisab=is_above_nisab,
        zakat_due=round(zakat_due, 2)
    )
