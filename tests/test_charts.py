"""比較チャート生成のスモークテスト."""

from __future__ import annotations

from nmincity.viz.charts import places_radar_chart, places_reach_bar_chart


def _profiles():
    return {
        "天王寺区": {"education": 0.8, "nature": 0.4, "goods": 0.9},
        "住吉区": {"education": 0.5, "nature": 0.7, "goods": 0.6},
    }


def test_places_radar_chart_writes_html(tmp_path):
    out = tmp_path / "radar.html"
    places_radar_chart(_profiles(), "比較", str(out))

    text = out.read_text(encoding="utf-8")
    # plotly はラベルを unicode エスケープするため、チャート種別で検証する
    assert "scatterpolar" in text.lower()
    assert out.stat().st_size > 0


def test_places_reach_bar_chart_writes_html(tmp_path):
    out = tmp_path / "bar.html"
    places_reach_bar_chart(_profiles(), "比較", str(out))

    assert out.exists()
    assert out.stat().st_size > 0
