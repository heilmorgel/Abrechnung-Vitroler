from backend.app.calc.fernwaerme import FernwaermeInput, allocate_fernwaerme


def test_fernwaerme_excel_logic():
    # Synthetic period matching Excel algorithm
    data = FernwaermeInput(
        wmz_eg=100,
        wmz_1og=200,
        wmz_2og=100,
        wmz_gesamt=500,  # => WW heat = 100
        ww_eg=2,
        ww_1og=None,
        ww_2og=3,
        ww_gesamt=10,  # => WW 1OG residual = 5
        ww_1og_residual=True,
    )
    result = allocate_fernwaerme(1000.0, data)
    # HZ share 400/500=0.8 => 800; WW 0.2 => 200
    assert result.details["kosten_hz"] == 800.0
    assert result.details["kosten_ww"] == 200.0
    # HZ: EG 100/400=0.25 => 200; 1OG 0.5 => 400; 2OG 0.25 => 200
    # WW: EG 2/10=0.2 => 40; 1OG 5/10=0.5 => 100; 2OG 3/10=0.3 => 60
    assert result.amounts["EG"] == 240.0
    assert result.amounts["1OG"] == 500.0
    assert result.amounts["2OG"] == 260.0
    assert abs(sum(result.amounts.values()) - 1000.0) < 0.01


def test_fernwaerme_direct_ww_1og():
    data = FernwaermeInput(
        wmz_eg=100,
        wmz_1og=100,
        wmz_2og=100,
        wmz_gesamt=400,
        ww_eg=1,
        ww_1og=1,
        ww_2og=1,
        ww_gesamt=3,
        ww_1og_residual=False,
    )
    result = allocate_fernwaerme(300.0, data)
    assert abs(sum(result.amounts.values()) - 300.0) < 0.01
