"""folium による MVP 地図出力."""

from __future__ import annotations

from pathlib import Path
import struct
import zlib

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


def walkability_map(lines: list[tuple[list[tuple[float, float]], float]], place: str) -> folium.Map:
    """街路区間を歩行環境の質で色分けした地図を返す."""

    points = [point for coords, _quality in lines for point in coords]
    if points:
        center_lat = sum(lat for lat, _lon in points) / len(points)
        center_lon = sum(lon for _lat, lon in points) / len(points)
    else:
        center_lat, center_lon = 35.0, 139.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")
    for coords, quality in lines:
        folium.PolyLine(
            locations=coords,
            color=_quality_color(quality),
            weight=4,
            opacity=0.78,
            popup=f"Q_edge={quality:.3f}",
        ).add_to(m)

    m.get_root().html.add_child(folium.Element(_walk_legend_html(place)))
    return m


def time_of_day_map(points_by_bucket: dict[str, list[tuple[float, float, float]]], place: str) -> folium.Map:
    """時間帯ごとに ``(lat, lon, S(t))`` 点群を切替表示する地図を返す."""

    all_points = [point for points in points_by_bucket.values() for point in points]
    if all_points:
        center_lat = sum(lat for lat, _lon, _score in all_points) / len(all_points)
        center_lon = sum(lon for _lat, lon, _score in all_points) / len(all_points)
    else:
        center_lat, center_lon = 35.0, 139.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")
    for bucket, points in points_by_bucket.items():
        show = bucket == "daytime"
        group = folium.FeatureGroup(name=bucket, show=show)
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
                popup=f"{bucket}: S={score:.3f} / {label}",
            ).add_to(group)
        group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_legend_html(f"時間帯別 n分都市度: {place}")))
    return m


def sq_scatter(points: list[tuple[float, float, str]], place: str, path: str) -> None:
    """起点別の ``S`` と ``Q`` を並置する散布図 PNG を保存する."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:  # pragma: no cover - optional dependency fallback
        _simple_scatter_png(points, output)
        return

    xs = [s for s, _q, _label in points]
    ys = [q for _s, q, _label in points]
    colors = [LABEL_COLORS.get(label, "#6b7280") for _s, _q, label in points]

    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    ax.scatter(xs, ys, c=colors, s=28, alpha=0.78, edgecolors="white", linewidths=0.4)
    ax.axvline(0.5, color="#6b7280", linewidth=1.0, linestyle="--")
    ax.axhline(0.5, color="#6b7280", linewidth=1.0, linestyle="--")
    ax.text(0.98, 0.04, "S高Q低", ha="right", va="bottom", transform=ax.transAxes, color="#374151")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_xlabel("S 近接性")
    ax.set_ylabel("Q 環境の質")
    ax.set_title(place)
    ax.grid(True, color="#e5e7eb", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)


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


def _quality_color(quality: float) -> str:
    q = max(0.0, min(1.0, float(quality)))
    red = int(220 + (21 - 220) * q)
    green = int(38 + (128 - 38) * q)
    blue = int(38 + (61 - 38) * q)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _walk_legend_html(place: str) -> str:
    return f"""
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #d1d5db;
      border-radius: 6px; font-size: 13px; box-shadow: 0 1px 4px #0002;">
      <div style="font-weight: 700; margin-bottom: 6px;">歩行環境の質: {place}</div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span>低</span>
        <span style="display:inline-block; width:96px; height:10px;
          background: linear-gradient(90deg, #dc2626, #15803d);"></span>
        <span>高</span>
      </div>
    </div>
    """


def _simple_scatter_png(points: list[tuple[float, float, str]], output: Path) -> None:
    width = 900
    height = 720
    margin_left = 86
    margin_right = 40
    margin_top = 40
    margin_bottom = 78
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    image = bytearray([255, 255, 255] * width * height)

    def set_pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            idx = (y * width + x) * 3
            image[idx : idx + 3] = bytes(color)

    def line(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        while True:
            set_pixel(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    def fill_circle(cx: int, cy: int, radius: int, color: tuple[int, int, int]) -> None:
        r2 = radius * radius
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                    set_pixel(x, y, color)

    grid = (229, 231, 235)
    axis = (55, 65, 81)
    mid = (107, 114, 128)
    for step in range(11):
        x = margin_left + round(plot_w * step / 10)
        y = margin_top + round(plot_h * step / 10)
        line(x, margin_top, x, margin_top + plot_h, grid)
        line(margin_left, y, margin_left + plot_w, y, grid)
    line(margin_left, margin_top + plot_h, margin_left + plot_w, margin_top + plot_h, axis)
    line(margin_left, margin_top, margin_left, margin_top + plot_h, axis)
    mid_x = margin_left + round(plot_w * 0.5)
    mid_y = margin_top + round(plot_h * 0.5)
    line(mid_x, margin_top, mid_x, margin_top + plot_h, mid)
    line(margin_left, mid_y, margin_left + plot_w, mid_y, mid)

    for s, q, label in points:
        x = margin_left + round(plot_w * max(0.0, min(1.0, s)))
        y = margin_top + round(plot_h * (1.0 - max(0.0, min(1.0, q))))
        color = _hex_to_rgb(LABEL_COLORS.get(label, "#6b7280"))
        fill_circle(x, y, 5, color)

    rows = [bytes(image[y * width * 3 : (y + 1) * width * 3]) for y in range(height)]
    raw = b"".join(b"\x00" + row for row in rows)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += _png_chunk(b"IDAT", zlib.compress(raw, 9))
    png += _png_chunk(b"IEND", b"")
    output.write_bytes(png)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    hex_value = value.lstrip("#")
    return int(hex_value[0:2], 16), int(hex_value[2:4], 16), int(hex_value[4:6], 16)
