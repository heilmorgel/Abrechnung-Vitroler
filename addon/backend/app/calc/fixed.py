from __future__ import annotations

from ..models import AllocationResult, Method, PercentShares, Scope


def allocate_fixed(scope: Scope, amount: float, percent: PercentShares) -> AllocationResult:
    shares_pct = percent.as_unit_dict()
    shares = {u: v / 100.0 for u, v in shares_pct.items()}
    amounts = {u: round(amount * s, 2) for u, s in shares.items()}
    # Fix rounding drift on last unit
    drift = round(amount - sum(amounts.values()), 2)
    if drift:
        amounts["2OG"] = round(amounts["2OG"] + drift, 2)
    return AllocationResult(
        method=Method.FIX_PROZENT,
        scope=scope,
        amount=amount,
        amounts=amounts,
        shares=shares,
        details={"percent": shares_pct},
    )
