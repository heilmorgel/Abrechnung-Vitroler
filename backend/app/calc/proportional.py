from __future__ import annotations

from ..models import AllocationResult, Method, Scope


def allocate_proportional(
    scope: Scope,
    amount: float,
    consumption: dict[str, float],
) -> AllocationResult:
    """Split by absolute consumption per unit (EG/1OG/2OG)."""
    for u in ("EG", "1OG", "2OG"):
        if u not in consumption:
            raise ValueError(f"Verbrauch für {u} fehlt")
        if consumption[u] < 0:
            raise ValueError(f"Verbrauch für {u} darf nicht negativ sein")

    total = sum(consumption[u] for u in ("EG", "1OG", "2OG"))
    if total <= 0:
        raise ValueError("Gesamtverbrauch muss > 0 sein")

    shares = {u: consumption[u] / total for u in ("EG", "1OG", "2OG")}
    amounts = {u: round(amount * shares[u], 2) for u in shares}
    drift = round(amount - sum(amounts.values()), 2)
    if drift:
        amounts["2OG"] = round(amounts["2OG"] + drift, 2)

    return AllocationResult(
        method=Method.VERBRAUCH,
        scope=scope,
        amount=amount,
        amounts=amounts,
        shares=shares,
        details={"consumption": consumption, "total": total},
    )
