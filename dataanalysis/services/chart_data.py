"""
Build Chart.js-ready config for analytics visualizations.
"""
import json
import numpy as np
import pandas as pd


def _serialize(obj):
    """Convert numpy types to Python native for JSON."""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def control_chart_config(labels, values, center, ucl, lcl, title, point_label="Value"):
    """One control chart: points + center, UCL, LCL lines."""
    n = len(labels)
    return {
        "type": "line",
        "title": title,
        "labels": [_serialize(i) for i in labels],
        "datasets": [
            {
                "label": point_label,
                "data": [_serialize(v) for v in values],
                "borderColor": "rgb(54, 162, 235)",
                "backgroundColor": "rgba(54, 162, 235, 0.1)",
                "fill": False,
                "tension": 0.1,
                "pointRadius": 4,
            },
            {
                "label": "Center",
                "data": [center] * n,
                "borderColor": "rgb(0, 128, 0)",
                "borderDash": [4, 4],
                "fill": False,
                "pointRadius": 0,
            },
            {
                "label": "UCL",
                "data": [ucl] * n,
                "borderColor": "rgb(220, 53, 69)",
                "borderDash": [2, 2],
                "fill": False,
                "pointRadius": 0,
            },
            {
                "label": "LCL",
                "data": [lcl] * n,
                "borderColor": "rgb(220, 53, 69)",
                "borderDash": [2, 2],
                "fill": False,
                "pointRadius": 0,
            },
        ],
    }


def build_xbar_r_charts(result, variable_name):
    """Two charts: X-bar and R."""
    xbar = result.get("Xbar") or {}
    r = result.get("R") or {}
    charts = []
    if xbar.get("values"):
        n = len(xbar["values"])
        charts.append(
            control_chart_config(
                list(range(1, n + 1)),
                xbar["values"],
                xbar["center"],
                xbar["UCL"],
                xbar["LCL"],
                f"X-bar Chart — {variable_name}",
                "X-bar",
            )
        )
    if r.get("values"):
        n = len(r["values"])
        charts.append(
            control_chart_config(
                list(range(1, n + 1)),
                r["values"],
                r["center"],
                r["UCL"],
                r["LCL"],
                f"R Chart — {variable_name}",
                "R",
            )
        )
    return charts


def build_xbar_s_charts(result, variable_name):
    """Two charts: X-bar and S."""
    xbar = result.get("Xbar") or {}
    s = result.get("S") or {}
    charts = []
    if xbar.get("values"):
        n = len(xbar["values"])
        charts.append(
            control_chart_config(
                list(range(1, n + 1)),
                xbar["values"],
                xbar["center"],
                xbar["UCL"],
                xbar["LCL"],
                f"X-bar Chart — {variable_name}",
                "X-bar",
            )
        )
    if s.get("values"):
        n = len(s["values"])
        charts.append(
            control_chart_config(
                list(range(1, n + 1)),
                s["values"],
                s["center"],
                s["UCL"],
                s["LCL"],
                f"S Chart — {variable_name}",
                "S",
            )
        )
    return charts


def build_i_mr_charts(result, variable_name):
    """Two charts: Individuals and Moving Range."""
    i = result.get("I") or {}
    mr = result.get("MR") or {}
    charts = []
    if i.get("values"):
        n = len(i["values"])
        charts.append(
            control_chart_config(
                list(range(1, n + 1)),
                i["values"],
                i["center"],
                i["UCL"],
                i["LCL"],
                f"Individuals Chart — {variable_name}",
                "Value",
            )
        )
    if mr.get("values"):
        n = len(mr["values"])
        charts.append(
            control_chart_config(
                list(range(1, n + 1)),
                mr["values"],
                mr["center"],
                mr["UCL"],
                mr["LCL"],
                f"Moving Range Chart — {variable_name}",
                "MR",
            )
        )
    return charts


def build_histogram(series, bins=15, title="Distribution", xlabel="Value"):
    """Histogram: bin edges (as labels) and counts."""
    s = pd.Series(series).dropna()
    if s.empty or not np.issubdtype(s.dtype, np.number):
        return None
    counts, bin_edges = np.histogram(s, bins=bins)
    # Use bin centers as labels for display
    bin_centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)]
    return {
        "type": "bar",
        "title": title,
        "labels": [_serialize(round(c, 4)) for c in bin_centers],
        "datasets": [
            {
                "label": "Count",
                "data": [_serialize(c) for c in counts],
                "backgroundColor": "rgba(54, 162, 235, 0.6)",
                "borderColor": "rgb(54, 162, 235)",
                "borderWidth": 1,
            }
        ],
    }


def build_capability_chart(series, usl=None, lsl=None, mean=None, title="Process Distribution"):
    """Histogram; reference line values passed for display in caption."""
    chart = build_histogram(series, bins=min(20, max(10, len(series) // 5)), title=title)
    if not chart:
        return None
    chart["reference_lines"] = []
    if lsl is not None:
        chart["reference_lines"].append({"value": float(lsl), "label": "LSL"})
    if mean is not None:
        chart["reference_lines"].append({"value": float(mean), "label": "Mean"})
    if usl is not None:
        chart["reference_lines"].append({"value": float(usl), "label": "USL"})
    return chart


def build_regression_chart(x, y, slope, intercept, x_var, y_var):
    """Scatter of (x,y) plus regression line."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if len(x) < 2:
        return None
    x_min, x_max = float(x.min()), float(x.max())
    y_pred_line = [intercept + slope * x_min, intercept + slope * x_max]
    # Scatter points
    scatter_data = [{"x": _serialize(xi), "y": _serialize(yi)} for xi, yi in zip(x, y)]
    return {
        "type": "scatter",
        "title": f"Regression: {y_var} vs {x_var}",
        "datasets": [
            {
                "label": "Data",
                "data": scatter_data,
                "backgroundColor": "rgba(54, 162, 235, 0.6)",
                "borderColor": "rgb(54, 162, 235)",
                "pointRadius": 5,
            },
            {
                "label": "Fit",
                "data": [
                    {"x": x_min, "y": y_pred_line[0]},
                    {"x": x_max, "y": y_pred_line[1]},
                ],
                "borderColor": "rgb(220, 53, 69)",
                "borderWidth": 2,
                "pointRadius": 0,
                "type": "line",
            },
        ],
    }


def build_descriptive_histogram(series, title="Distribution"):
    """Single variable histogram for descriptive view."""
    return build_histogram(series, title=title)
