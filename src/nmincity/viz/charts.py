"""plotly による感度分析・シナリオ比較チャート."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import plotly.graph_objects as go

from nmincity.config import CATEGORY_NAMES


def sensitivity_chart(sensitivity: Mapping[str, float], place: str, path: str) -> None:
    """カテゴリ別の ``Δmean_S`` 横棒グラフを HTML 保存する."""

    items = sorted(sensitivity.items(), key=lambda item: item[1])
    categories = [CATEGORY_NAMES.get(category, category) for category, _value in items]
    values = [value for _category, value in items]
    colors = ["#dc2626" if value < 0 else "#15803d" for value in values]

    fig = go.Figure(
        data=[
            go.Bar(
                x=values,
                y=categories,
                orientation="h",
                marker_color=colors,
                hovertemplate="%{y}<br>Δmean S=%{x:.4f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=f"重み感度分析: {place}",
        xaxis_title="Δmean S",
        yaxis_title="カテゴリ",
        template="plotly_white",
    )
    _write_html(fig, path)


def scenario_chart(comparison: Mapping[str, Mapping[str, float]], place: str, path: str) -> None:
    """シナリオ別 mean S の棒グラフを HTML 保存する."""

    names = list(comparison)
    means = [comparison[name].get("mean", 0.0) for name in names]
    mins = [comparison[name].get("min", 0.0) for name in names]
    maxes = [comparison[name].get("max", 0.0) for name in names]
    upper = [max(0.0, high - mean) for high, mean in zip(maxes, means)]
    lower = [max(0.0, mean - low) for low, mean in zip(mins, means)]

    fig = go.Figure(
        data=[
            go.Bar(
                x=[_scenario_name(name) for name in names],
                y=means,
                error_y={"type": "data", "array": upper, "arrayminus": lower},
                marker_color=["#2563eb" if name != "proposals_applied" else "#15803d" for name in names],
                hovertemplate="%{x}<br>mean S=%{y:.3f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=f"シナリオ比較: {place}",
        xaxis_title="シナリオ",
        yaxis_title="mean S",
        yaxis_range=[0, 1],
        template="plotly_white",
    )
    _write_html(fig, path)


def reach_rate_chart(rates: Mapping[str, float], place: str, path: str) -> None:
    """カテゴリ別到達率の棒グラフを HTML 保存する."""

    categories = [CATEGORY_NAMES.get(category, category) for category in rates]
    values = [rates[category] for category in rates]
    fig = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                marker_color="#0f766e",
                hovertemplate="%{x}<br>到達率=%{y:.3f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=f"カテゴリ別到達率: {place}",
        xaxis_title="カテゴリ",
        yaxis_title="到達率",
        yaxis_range=[0, 1],
        template="plotly_white",
    )
    _write_html(fig, path)


def _write_html(fig: go.Figure, path: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output), include_plotlyjs="cdn")


def _scenario_name(name: str) -> str:
    return {
        "baseline": "現状",
        "equal": "等重み",
        "education_heavy": "学ぶ重視",
        "nature_heavy": "自然重視",
        "proposals_applied": "提案実施後",
    }.get(name, name)
