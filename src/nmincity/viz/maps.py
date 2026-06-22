"""folium による MVP 地図出力."""

from __future__ import annotations

from pathlib import Path

import folium

from nmincity.config import score_label


LABEL_COLORS = {
    "良好": "#15803d",
    "要改善": "#f97316",
    "不足": "#dc2626",
}


def score_map(points: list[tuple[float, float, float]], place: str) -> folium.Map:
    """``(lat, lon, S)`` 点群をスコアラベル色で描画した地図を返す."""

    if points:
        center_lat = sum(lat for lat, _lon, _score in points) / len(points)
        center_lon = sum(lon for _lat, lon, _score in points) / len(points)
    else:
        center_lat, center_lon = 35.0, 139.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")
    for lat, lon, score in points:
        label = score_label(score)
        color = LABEL_COLORS[label]
        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.72,
            weight=1,
            popup=f"S={score:.3f} / {label}",
        ).add_to(m)

    legend = _legend_html(place)
    m.get_root().html.add_child(folium.Element(legend))
    return m


def save_map(m: folium.Map, path: str) -> None:
    """親ディレクトリを作成して folium 地図 HTML を保存する."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output))


def _legend_html(place: str) -> str:
    rows = "".join(
        f'<div><span style="background:{color};"></span>{label}</div>'
        for label, color in LABEL_COLORS.items()
    )
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">n分都市度: {place}</div>
      <style>
        .nmincity-legend span {{
          display: inline-block; width: 10px; height: 10px; margin-right: 6px;
          border-radius: 999px;
        }}
      </style>
      <div class="nmincity-legend">{rows}</div>
    </div>
    """
