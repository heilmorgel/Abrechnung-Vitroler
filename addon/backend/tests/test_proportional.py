from backend.app.calc.proportional import allocate_proportional
from backend.app.models import Scope


def test_wasser_split():
    result = allocate_proportional(
        Scope.WASSER_ABWASSER,
        90.0,
        {"EG": 45, "1OG": 30, "2OG": 15},
    )
    assert result.amounts["EG"] == 45.0
    assert result.amounts["1OG"] == 30.0
    assert result.amounts["2OG"] == 15.0


def test_strom_split():
    result = allocate_proportional(
        Scope.STROM,
        100.0,
        {"EG": 50, "1OG": 25, "2OG": 25},
    )
    assert result.amounts["EG"] == 50.0
