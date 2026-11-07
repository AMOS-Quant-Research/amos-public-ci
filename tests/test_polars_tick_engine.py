import pytest
import polars as pl
from modules.polars_tick_engine import scan_quotes, quality_report, export_validated_parquet

def write_ticks(path, bid=(2300.0, 2301.0), ask=(2300.2, 2301.2)):
    pl.DataFrame({
        "ts_event": pl.Series(["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"]).str.to_datetime(time_zone="UTC"),
        "bid": list(bid), "ask": list(ask),
    }).write_parquet(path)

def test_valid_round_trip(tmp_path):
    src, dst = tmp_path / "in.parquet", tmp_path / "out.parquet"
    write_ticks(src)
    report = export_validated_parquet(src, dst)
    assert report["rows"] == 2
    assert report["invalid_quotes"] == 0
    assert pl.read_parquet(dst)["bid"].to_list() == [2300.0, 2301.0]
    assert scan_quotes(dst).collect()["spread"].to_list() == pytest.approx([0.2, 0.2])

def test_crossed_market_rejected(tmp_path):
    src = tmp_path / "in.parquet"
    write_ticks(src, ask=(2299.0, 2301.2))
    assert quality_report(scan_quotes(src))["invalid_quotes"] == 1
    with pytest.raises(ValueError, match="quality gate"):
        export_validated_parquet(src, tmp_path / "out.parquet")

def test_missing_column_rejected(tmp_path):
    src = tmp_path / "in.parquet"
    pl.DataFrame({"bid": [1.0]}).write_parquet(src)
    with pytest.raises(ValueError, match="Missing"):
        scan_quotes(src)
