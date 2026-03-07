"""
Export analytics results to PDF and session-style text (like session output).
Includes chart images generated with matplotlib.
"""
import io
from datetime import date

import numpy as np
import pandas as pd

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    Image = None
    inch = 72

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def _fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}" if abs(v) < 1e-4 or abs(v) >= 1e4 else f"{v:.4f}"
    return str(v)


def result_to_table_data(result, result_type):
    """Convert result dict or descriptive structure to table rows for reportlab."""
    if result_type == "descriptive" and "rows" in result and "columns" in result:
        cols = result["columns"]
        rows = [[_fmt(cell) for cell in row] for row in result["rows"]]
        return [cols] + rows
    # Key-value style; for control charts also flatten Xbar/R or I/MR summary
    if isinstance(result, dict):
        rows = []
        for k, v in result.items():
            if k in ("values", "datasets", "reference_lines"):
                continue
            if isinstance(v, dict) and k in ("Xbar", "R", "S", "I", "MR"):
                for stat in ("center", "UCL", "LCL"):
                    if stat in v and v[stat] is not None:
                        rows.append([f"{k} {stat.title()}", _fmt(v[stat])])
                continue
            if isinstance(v, (list, dict)):
                continue
            rows.append([str(k), _fmt(v)])
        return [["Statistic", "Value"]] + rows if rows else []
    return []


def _chart_to_png(fig, dpi=100):
    """Render matplotlib figure to PNG bytes. Closes fig."""
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        return buf.read()
    finally:
        plt.close(fig)


def draw_control_chart_png(labels, values, center, ucl, lcl, title):
    """Draw one control chart (line + center/UCL/LCL), return PNG bytes."""
    if not MATPLOTLIB_AVAILABLE or not labels or values is None:
        return None
    fig, ax = plt.subplots(figsize=(6, 3))
    x = list(range(1, len(values) + 1))
    ax.plot(x, values, "b.-", label="Value", markersize=4)
    ax.axhline(center, color="green", linestyle="--", label="Center")
    ax.axhline(ucl, color="red", linestyle=":", label="UCL")
    ax.axhline(lcl, color="red", linestyle=":", label="LCL")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Subgroup / Observation")
    ax.legend(loc="best", fontsize=7)
    ax.grid(True, alpha=0.3)
    return _chart_to_png(fig)


def draw_histogram_png(series, title, usl=None, lsl=None, mean_val=None):
    """Draw histogram, optionally with LSL/Mean/USL lines. series: array-like. Returns PNG bytes."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    try:
        s = pd.Series(series).dropna()
        if s.empty or not np.issubdtype(s.dtype, np.number):
            return None
    except Exception:
        return None
    fig, ax = plt.subplots(figsize=(6, 3))
    n_bins = min(20, max(10, len(s) // 5))
    ax.hist(s, bins=n_bins, color="steelblue", edgecolor="white", alpha=0.8)
    if lsl is not None:
        ax.axvline(lsl, color="red", linestyle="--", linewidth=1.5, label=f"LSL = {lsl:.4g}")
    if mean_val is not None:
        ax.axvline(mean_val, color="green", linestyle="-", linewidth=1.5, label=f"Mean = {mean_val:.4g}")
    if usl is not None:
        ax.axvline(usl, color="red", linestyle="--", linewidth=1.5, label=f"USL = {usl:.4g}")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Value")
    ax.set_ylabel("Count")
    if any(x is not None for x in (lsl, mean_val, usl)):
        ax.legend(loc="best", fontsize=7)
    ax.grid(True, alpha=0.3)
    return _chart_to_png(fig)


def draw_regression_png(x, y, slope, intercept, x_var, y_var):
    """Draw scatter + regression line. Returns PNG bytes."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if len(x) < 2:
        return None
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.scatter(x, y, alpha=0.6, s=20, color="steelblue", edgecolors="navy")
    x_min, x_max = x.min(), x.max()
    y_fit = intercept + slope * np.array([x_min, x_max])
    ax.plot([x_min, x_max], y_fit, "r-", linewidth=2, label="Fit")
    ax.set_title(f"Regression: {y_var} vs {x_var}", fontsize=10)
    ax.set_xlabel(x_var)
    ax.set_ylabel(y_var)
    ax.legend(loc="best", fontsize=7)
    ax.grid(True, alpha=0.3)
    return _chart_to_png(fig)


def build_chart_images(analysis, result, result_type, df, var_name, var2_name, usl=None, lsl=None):
    """Build list of (title, png_bytes) for embedding in PDF. Returns [] if matplotlib unavailable."""
    if not MATPLOTLIB_AVAILABLE or result is None:
        return []
    images = []
    try:
        if analysis in ("xbar_r", "xbar_s") and result.get("chart"):
            xbar = result.get("Xbar") or {}
            r_or_s = result.get("R") or result.get("S") or {}
            if xbar.get("values"):
                img = draw_control_chart_png(
                    list(range(1, len(xbar["values"]) + 1)),
                    xbar["values"],
                    xbar["center"],
                    xbar["UCL"],
                    xbar["LCL"],
                    f"X-bar Chart — {var_name or ''}",
                )
                if img:
                    images.append((f"X-bar Chart — {var_name or ''}", img))
            if r_or_s.get("values"):
                img = draw_control_chart_png(
                    list(range(1, len(r_or_s["values"]) + 1)),
                    r_or_s["values"],
                    r_or_s["center"],
                    r_or_s["UCL"],
                    r_or_s["LCL"],
                    f"{'R' if 'R' in result else 'S'} Chart — {var_name or ''}",
                )
                if img:
                    images.append((f"{'R' if 'R' in result else 'S'} Chart — {var_name or ''}", img))
        elif analysis == "i_mr" and result.get("I"):
            i, mr = result.get("I") or {}, result.get("MR") or {}
            if i.get("values"):
                img = draw_control_chart_png(
                    list(range(1, len(i["values"]) + 1)), i["values"],
                    i["center"], i["UCL"], i["LCL"],
                    f"Individuals — {var_name or ''}",
                )
                if img:
                    images.append((f"Individuals — {var_name or ''}", img))
            if mr.get("values"):
                img = draw_control_chart_png(
                    list(range(1, len(mr["values"]) + 1)), mr["values"],
                    mr["center"], mr["UCL"], mr["LCL"],
                    f"Moving Range — {var_name or ''}",
                )
                if img:
                    images.append((f"Moving Range — {var_name or ''}", img))
        elif analysis == "capability" and var_name and var_name in df.columns:
            s = df[var_name].dropna()
            if not s.empty:
                img = draw_histogram_png(
                    s, f"Distribution — {var_name}",
                    usl=result.get("USL"), lsl=result.get("LSL"), mean_val=result.get("Mean"),
                )
                if img:
                    images.append((f"Distribution — {var_name}", img))
        elif analysis == "descriptive" and result.get("columns"):
            cols = [c for c in result["columns"] if c != "Statistic"]
            if cols and df is not None and cols[0] in df.columns:
                s = df[cols[0]].dropna()
                if not s.empty:
                    img = draw_histogram_png(s, f"Distribution — {cols[0]}")
                    if img:
                        images.append((f"Distribution — {cols[0]}", img))
        elif analysis == "regression" and var_name and var2_name and var2_name in df.columns:
            img = draw_regression_png(
                df[var2_name], df[var_name],
                result["Slope"], result["Intercept"],
                var2_name, var_name,
            )
            if img:
                images.append((f"Regression: {var_name} vs {var2_name}", img))
    except Exception:
        pass
    return images


def build_pdf(dataset_name, analysis_label, result, result_type, variable=None, variable2=None, chart_images=None):
    """Build PDF buffer with report content. chart_images: list of (title, png_bytes). Returns bytes."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("PDF export requires the reportlab package. Install with: pip install reportlab")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=12,
    )
    body = []
    body.append(Paragraph("Data Analytics Report", title_style))
    body.append(Paragraph(f"Dataset: {dataset_name}", styles["Normal"]))
    body.append(Paragraph(f"Analysis: {analysis_label}", styles["Normal"]))
    if variable:
        body.append(Paragraph(f"Variable(s): {variable}" + (f", {variable2}" if variable2 else ""), styles["Normal"]))
    body.append(Paragraph(f"Date: {date.today().isoformat()}", styles["Normal"]))
    body.append(Spacer(1, 0.25 * inch))

    # Charts first (so data table follows)
    if chart_images:
        for title, png_bytes in chart_images:
            body.append(Paragraph(title, styles["Heading2"]))
            try:
                img = Image(io.BytesIO(png_bytes), width=5.5 * inch, height=2.25 * inch)
                body.append(img)
            except Exception:
                pass
            body.append(Spacer(1, 0.15 * inch))

    body.append(Paragraph("Results", styles["Heading2"]))
    table_data = result_to_table_data(result, result_type)
    if table_data:
        t = Table(table_data, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]
            )
        )
        body.append(t)
    else:
        body.append(Paragraph("No table output for this analysis.", styles["Normal"]))

    doc.build(body)
    return buf.getvalue()


def build_session_txt(dataset_name, analysis_label, result, result_type, variable=None, variable2=None):
    """Build session-window-style plain text output. Returns str."""
    lines = [
        "=" * 60,
        "Data Analytics — Session Output",
        "=" * 60,
        f"Dataset: {dataset_name}",
        f"Analysis: {analysis_label}",
    ]
    if variable:
        lines.append(f"Variable(s): {variable}" + (f", {variable2}" if variable2 else ""))
    lines.append(f"Date: {date.today().isoformat()}")
    lines.append("")

    table_data = result_to_table_data(result, result_type)
    if table_data:
        col_widths = [max(len(_fmt(row[i])) for row in table_data) for i in range(len(table_data[0]))]
        for i, row in enumerate(table_data):
            line = "  ".join(str(c).ljust(col_widths[j]) for j, c in enumerate(row))
            lines.append(line)
            if i == 0:
                lines.append("-" * len(line))
    else:
        lines.append("(No table output for this analysis.)")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
