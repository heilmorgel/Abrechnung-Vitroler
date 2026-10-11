from backend.app.calc.fixed import allocate_fixed
from backend.app.models import PercentShares, Scope


def test_fixed_default_split():
    result = allocate_fixed(Scope.STROM, 100.0, PercentShares())
    assert result.amounts["EG"] == 50.0
    assert result.amounts["1OG"] == 25.0
    assert result.amounts["2OG"] == 25.0
    assert abs(sum(result.amounts.values()) - 100.0) < 0.001


def test_fixed_custom():
    pct = PercentShares.model_validate({"EG": 40, "1OG": 35, "2OG": 25})
    result = allocate_fixed(Scope.WASSER_ABWASSER, 200.0, pct)
    assert result.amounts["EG"] == 80.0
    assert result.amounts["1OG"] == 70.0
    assert result.amounts["2OG"] == 50.0
