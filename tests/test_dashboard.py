"""統合ダッシュボード HTML 生成のテスト."""

from __future__ import annotations

from nmincity.viz.dashboard import build_dashboard


def test_build_dashboard_writes_panels_and_weights(tmp_path):
    out = tmp_path / "dash.html"
    build_dashboard(
        place="天王寺区",
        panels=[("近接性 S", "place_S.html"), ("環境の質 Q", "place_Q.html")],
        weight_rows=[
            {"name": "学ぶ", "weight": "0.18", "rationale": "中核機能", "reference": "出典X"},
        ],
        summary=[("起点数", "200"), ("S 平均", "0.42")],
        path=str(out),
    )

    text = out.read_text(encoding="utf-8")
    assert "天王寺区" in text
    # パネルが iframe で埋め込まれる
    assert 'src="place_S.html"' in text
    assert 'src="place_Q.html"' in text
    # 重み根拠表
    assert "学ぶ" in text
    assert "出典X" in text
    # サマリ
    assert "起点数" in text


def test_build_dashboard_escapes_html(tmp_path):
    out = tmp_path / "dash.html"
    build_dashboard(
        place="<script>",
        panels=[],
        weight_rows=[],
        summary=[],
        path=str(out),
    )

    text = out.read_text(encoding="utf-8")
    # ダッシュボードは JS を含まないため、生の <script タグが出てはいけない
    assert "<script" not in text
    assert "&lt;script&gt;" in text
