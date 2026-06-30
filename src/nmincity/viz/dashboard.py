"""地図・チャート・重み根拠を1枚にまとめた統合ダッシュボード HTML 生成."""

from __future__ import annotations

import html
from pathlib import Path
from collections.abc import Mapping, Sequence


def build_dashboard(
    *,
    place: str,
    panels: Sequence[tuple[str, str]],
    weight_rows: Sequence[Mapping[str, object]],
    summary: Sequence[tuple[str, str]],
    path: str,
    subtitle: str = "",
) -> None:
    """統合ダッシュボード HTML を1枚生成する.

    Parameters
    ----------
    place:
        対象地区名（見出しに表示）。
    panels:
        ``(タイトル, 埋め込む HTML ファイルへの相対パス)`` の列。iframe で並置する。
        S 地図と Q 地図を並べると §6.7.1 の「S と Q を合成せず並置」方針に沿う。
    weight_rows:
        重み根拠表の行。各要素は ``{"name", "weight", "rationale", "reference"}``。
    summary:
        ``(ラベル, 値)`` の要約統計列。
    path:
        出力 HTML パス。``panels`` の相対パスはこのファイルからの相対で解決される。
    """

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    panel_html = "\n".join(
        f"""
        <figure class="panel">
          <figcaption>{html.escape(title)}</figcaption>
          <iframe src="{html.escape(src)}" loading="lazy"></iframe>
        </figure>"""
        for title, src in panels
    )

    summary_html = "".join(
        f'<div class="stat"><span class="stat-label">{html.escape(label)}</span>'
        f'<span class="stat-value">{html.escape(value)}</span></div>'
        for label, value in summary
    )

    rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('name', '')))}</td>"
        f"<td class=\"num\">{html.escape(str(row.get('weight', '')))}</td>"
        f"<td>{html.escape(str(row.get('rationale', '')))}</td>"
        f"<td>{html.escape(str(row.get('reference', '')))}</td>"
        "</tr>"
        for row in weight_rows
    )

    sub = f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle else ""

    document = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>n分都市ダッシュボード: {html.escape(place)}</title>
<style>
  :root {{ --fg:#1f2937; --muted:#6b7280; --line:#e5e7eb; --accent:#0f766e; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: system-ui, "Hiragino Sans", "Noto Sans JP", sans-serif;
         color: var(--fg); background:#f8fafc; }}
  header {{ padding: 20px 28px; background:#fff; border-bottom:1px solid var(--line); }}
  header h1 {{ margin:0; font-size:20px; }}
  .subtitle {{ margin:6px 0 0; color: var(--muted); font-size:13px; }}
  main {{ padding: 24px 28px; max-width: 1280px; margin: 0 auto; }}
  section {{ margin-bottom: 32px; }}
  section h2 {{ font-size:16px; border-left:4px solid var(--accent); padding-left:10px; }}
  .summary {{ display:flex; flex-wrap:wrap; gap:12px; }}
  .stat {{ background:#fff; border:1px solid var(--line); border-radius:8px;
          padding:10px 14px; min-width:120px; }}
  .stat-label {{ display:block; color:var(--muted); font-size:12px; }}
  .stat-value {{ display:block; font-size:18px; font-weight:700; }}
  .panels {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap:18px; }}
  .panel {{ margin:0; background:#fff; border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
  .panel figcaption {{ padding:8px 12px; font-weight:700; font-size:13px; border-bottom:1px solid var(--line); }}
  .panel iframe {{ width:100%; height:460px; border:0; display:block; }}
  table {{ width:100%; border-collapse: collapse; background:#fff; font-size:13px; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ background:#f1f5f9; }}
  td.num {{ text-align:right; white-space:nowrap; }}
  .note {{ color:var(--muted); font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>n分都市化支援ツール ダッシュボード — {html.escape(place)}</h1>
  {sub}
</header>
<main>
  <section>
    <h2>サマリ</h2>
    <div class="summary">{summary_html}</div>
  </section>
  <section>
    <h2>地図（近接性 S と環境の質 Q は合成せず並置）</h2>
    <div class="panels">{panel_html}</div>
  </section>
  <section>
    <h2>重みづけの根拠</h2>
    <table>
      <thead><tr><th>カテゴリ</th><th>重み</th><th>設計意図</th><th>出典</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p class="note">重みは事例・施策（できればマスタープラン）に基づき調整する。出典欄を埋めること。</p>
  </section>
</main>
</body>
</html>
"""
    output.write_text(document, encoding="utf-8")
