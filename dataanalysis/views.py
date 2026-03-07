from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from .models import Datasets, DatasetFile, ManualRecord, Variables
from .forms import DatasetForm, FileUploadForm, ManualRecordForm, AnalyticsForm
from .services.data_import import get_dataset_dataframe, process_uploaded_file, create_variables_from_dataframe
from .services import analytics as ana
from .services.chart_data import (
    build_xbar_r_charts,
    build_xbar_s_charts,
    build_i_mr_charts,
    build_histogram,
    build_capability_chart,
    build_regression_chart,
    build_descriptive_histogram,
)
from .services.report_export import build_pdf, build_session_txt, build_chart_images
import pandas as pd
import json


def _run_analysis(df, analysis, var_name, var2_name, subgroup_size, usl, lsl, mu0):
    """Run analysis and return (result, result_type) or (None, None)."""
    numeric_cols = list(df.select_dtypes(include=["number"]).columns)
    if not var_name and numeric_cols:
        var_name = numeric_cols[0]
    if var_name and var_name not in df.columns:
        return None, None
    result, result_type = None, "table"
    if analysis == "descriptive":
        raw = ana.run_all_descriptive(df, columns=numeric_cols)
        if raw:
            cols = list(raw.keys())
            stat_names = list(next(iter(raw.values())).keys())
            result = {"columns": ["Statistic"] + cols, "rows": [[sn] + [raw[c].get(sn) for c in cols] for sn in stat_names]}
        else:
            result = {"columns": [], "rows": []}
        result_type = "descriptive"
    elif analysis == "xbar_r" and var_name:
        data = df[var_name].dropna().to_numpy()
        if len(data) % subgroup_size != 0:
            data = data[: (len(data) // subgroup_size) * subgroup_size]
        result = ana.xbar_r_chart(data, subgroup_size=subgroup_size)
    elif analysis == "xbar_s" and var_name:
        data = df[var_name].dropna().to_numpy()
        if len(data) % subgroup_size != 0:
            data = data[: (len(data) // subgroup_size) * subgroup_size]
        result = ana.xbar_s_chart(data, subgroup_size=subgroup_size)
    elif analysis == "i_mr" and var_name:
        result = ana.i_mr_chart(df[var_name].dropna().to_numpy())
    elif analysis == "capability" and var_name and (usl is not None or lsl is not None):
        result = ana.capability_indices(df[var_name], usl=usl, lsl=lsl)
    elif analysis == "one_sample_t" and var_name and mu0 is not None:
        result = ana.one_sample_t(df[var_name], mu0=mu0)
    elif analysis == "two_sample_t" and var_name and var2_name and var2_name in df.columns:
        if pd.api.types.is_numeric_dtype(df[var2_name]):
            result = ana.two_sample_t(df[var_name], df[var2_name])
        else:
            groups = df.groupby(var2_name)[var_name].apply(list).to_dict()
            if len(groups) >= 2:
                result = ana.two_sample_t(list(groups.values())[0], list(groups.values())[1])
    elif analysis == "paired_t" and var_name and var2_name and var2_name in df.columns:
        result = ana.paired_t(df[var_name], df[var2_name])
    elif analysis == "anova" and var_name and var2_name and var2_name in df.columns:
        groups = df.groupby(var2_name)[var_name].apply(list).to_dict()
        result = ana.one_way_anova(groups)
    elif analysis == "regression" and var_name and var2_name and var2_name in df.columns:
        result = ana.simple_linear_regression(df[var2_name], df[var_name])
    return result, result_type


@login_required
def dataset_list(request):
    datasets = Datasets.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "dataanalysis/dataset_list.html", {"datasets": datasets})


@login_required
def dataset_create(request):
    if request.method == "POST":
        form = DatasetForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            messages.success(request, "Dataset created. Add data by uploading a file or entering records.")
            return redirect("dataanalysis:dataset_detail", pk=obj.pk)
    else:
        form = DatasetForm()
    return render(request, "dataanalysis/dataset_form.html", {"form": form, "title": "New Dataset"})


@login_required
def dataset_detail(request, pk):
    dataset = get_object_or_404(Datasets, pk=pk, owner=request.user)
    df = get_dataset_dataframe(dataset)
    numeric_cols = list(df.select_dtypes(include=["number"]).columns) if not df.empty else []
    variables = list(dataset.variables.values_list("name", flat=True))

    # File upload
    upload_form = FileUploadForm(initial={"file_type": "xlsx"})
    record_form = ManualRecordForm(dataset) if variables else None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "upload":
            upload_form = FileUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                f = upload_form.save(commit=False)
                f.dataset = dataset
                f.save()
                messages.success(request, "File uploaded and processed.")
                return redirect("dataanalysis:dataset_detail", pk=pk)
        elif action == "manual":
            if not variables:
                # First manual record: variable names (comma-separated) and values (comma-separated)
                names_str = (request.POST.get("variable_names") or "").strip()
                values_str = (request.POST.get("variable_values") or "").strip()
                if names_str and values_str:
                    names = [n.strip() for n in names_str.split(",") if n.strip()]
                    raw_vals = [v.strip() for v in values_str.split(",")]
                    if len(names) != len(raw_vals):
                        messages.warning(request, "Number of variable names must match number of values.")
                    else:
                        try:
                            values = {}
                            for n, v in zip(names, raw_vals):
                                try:
                                    values[n] = float(v)
                                except ValueError:
                                    values[n] = v
                            for name in names:
                                if not dataset.variables.filter(name=name).exists():
                                    Variables.objects.create(dataset=dataset, name=name, data_type="numeric")
                            ManualRecord.objects.create(dataset=dataset, values=values)
                            messages.success(request, "Record added. Variables created; you can add more records below.")
                            return redirect("dataanalysis:dataset_detail", pk=pk)
                        except Exception as e:
                            messages.warning(request, str(e))
                else:
                    messages.warning(request, "Enter variable names and values (comma-separated).")
            else:
                record_form = ManualRecordForm(dataset, request.POST)
                if record_form.is_valid():
                    values = record_form.get_values()
                    if values:
                        ManualRecord.objects.create(dataset=dataset, values=values)
                        messages.success(request, "Record added.")
                        return redirect("dataanalysis:dataset_detail", pk=pk)
                    messages.warning(request, "Enter at least one value.")

    # Paginate data table (100 rows per page)
    row_count = len(df)
    page_size = 100
    paginator = None
    page = None
    table_rows = []
    if not df.empty:
        paginator = Paginator(range(row_count), page_size)
        page_num = request.GET.get("page", 1)
        try:
            page = paginator.page(page_num)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)
        start = (page.number - 1) * page_size
        end = start + page_size
        df_page = df.iloc[start:end]
        for row in df_page.to_numpy():
            table_rows.append(["" if pd.isna(c) else c for c in row])

    context = {
        "dataset": dataset,
        "df_columns": list(df.columns) if not df.empty else [],
        "table_rows": table_rows,
        "row_count": row_count,
        "page": page,
        "paginator": paginator,
        "numeric_cols": numeric_cols,
        "variables": variables,
        "upload_form": upload_form,
        "record_form": record_form,
        "analytics_form": AnalyticsForm(),
    }
    return render(request, "dataanalysis/dataset_detail.html", context)


@login_required
def dataset_visualize(request, pk):
    """Quick visualization: histogram or run chart for one numeric variable."""
    dataset = get_object_or_404(Datasets, pk=pk, owner=request.user)
    df = get_dataset_dataframe(dataset)
    numeric_cols = list(df.select_dtypes(include=["number"]).columns) if not df.empty else []
    var_name = request.GET.get("variable") or (numeric_cols[0] if numeric_cols else None)
    chart_type = request.GET.get("chart_type", "histogram")

    chart = None
    if var_name and var_name in df.columns and pd.api.types.is_numeric_dtype(df[var_name]):
        s = df[var_name].dropna()
        if not s.empty:
            if chart_type == "run":
                chart = {
                    "type": "line",
                    "title": f"Run Chart — {var_name}",
                    "labels": list(range(1, len(s) + 1)),
                    "datasets": [
                        {
                            "label": var_name,
                            "data": s.tolist(),
                            "borderColor": "rgb(54, 162, 235)",
                            "backgroundColor": "rgba(54, 162, 235, 0.1)",
                            "fill": False,
                            "tension": 0.1,
                            "pointRadius": 2,
                        }
                    ],
                }
            else:
                chart = build_histogram(s, bins=min(20, max(10, len(s) // 5)), title=f"Distribution — {var_name}", xlabel=var_name)
                if chart:
                    chart["title"] = f"Histogram — {var_name}"
            if chart:
                cfg = {
                    "type": chart.get("type", "line"),
                    "data": {"labels": chart.get("labels", []), "datasets": chart.get("datasets", [])},
                    "options": {"responsive": True, "maintainAspectRatio": False, "scales": {"x": {"display": True}, "y": {"display": True, "beginAtZero": chart.get("type") == "bar"}}},
                }
                chart["config_json"] = json.dumps(cfg)

    return render(
        request,
        "dataanalysis/dataset_visualize.html",
        {"dataset": dataset, "numeric_cols": numeric_cols, "variable": var_name, "chart_type": chart_type, "chart": chart},
    )


@login_required
def dataset_delete(request, pk):
    dataset = get_object_or_404(Datasets, pk=pk, owner=request.user)
    if request.method == "POST":
        dataset.delete()
        messages.success(request, "Dataset deleted.")
        return redirect("dataanalysis:dataset_list")
    return render(request, "dataanalysis/dataset_confirm_delete.html", {"dataset": dataset})


@login_required
def run_analytics(request, pk):
    dataset = get_object_or_404(Datasets, pk=pk, owner=request.user)
    df = get_dataset_dataframe(dataset)
    if df.empty:
        messages.warning(request, "No data in this dataset.")
        return redirect("dataanalysis:dataset_detail", pk=pk)

    form = AnalyticsForm(request.GET or request.POST)
    if not form.is_valid():
        messages.warning(request, "Select an analysis and variable(s).")
        return redirect("dataanalysis:dataset_detail", pk=pk)

    analysis = form.cleaned_data["analysis"]
    var_name = form.cleaned_data.get("variable") or (request.GET.get("variable") or request.POST.get("variable"))
    var2_name = form.cleaned_data.get("variable2") or request.GET.get("variable2") or request.POST.get("variable2")
    subgroup_size = form.cleaned_data.get("subgroup_size") or 5
    usl = form.cleaned_data.get("usl")
    lsl = form.cleaned_data.get("lsl")
    mu0 = form.cleaned_data.get("mu0")

    numeric_cols = list(df.select_dtypes(include=["number"]).columns)
    if not var_name and numeric_cols:
        var_name = numeric_cols[0]
    if var_name and var_name not in df.columns:
        messages.error(request, f"Variable '{var_name}' not found.")
        return redirect("dataanalysis:dataset_detail", pk=pk)

    result, result_type = _run_analysis(df, analysis, var_name, var2_name, subgroup_size, usl, lsl, mu0)
    if result is None:
        messages.warning(request, "Could not run this analysis. Check variable selection and parameters.")
        return redirect("dataanalysis:dataset_detail", pk=pk)

    # Build chart data for visualization
    charts = []
    if result_type == "descriptive" and numeric_cols:
        h = build_descriptive_histogram(df[numeric_cols[0]], title=f"Distribution — {numeric_cols[0]}")
        if h:
            charts.append({"id": "desc-hist", "title": h.pop("title"), **h})
    elif analysis in ("xbar_r", "xbar_s", "i_mr") and result.get("chart"):
        if analysis == "xbar_r":
            chart_list = build_xbar_r_charts(result, var_name or "")
        elif analysis == "xbar_s":
            chart_list = build_xbar_s_charts(result, var_name or "")
        else:
            chart_list = build_i_mr_charts(result, var_name or "")
        for i, cfg in enumerate(chart_list):
            charts.append({"id": f"control-{i}", "title": cfg.pop("title"), **cfg})
    elif analysis == "capability" and result and var_name:
        cap_chart = build_capability_chart(
            df[var_name],
            usl=result.get("USL"),
            lsl=result.get("LSL"),
            mean=result.get("Mean"),
            title=f"Distribution — {var_name}",
        )
        if cap_chart:
            charts.append({"id": "cap-hist", "title": cap_chart.pop("title"), **cap_chart})
    elif analysis == "regression" and result and var_name and var2_name:
        reg_chart = build_regression_chart(
            df[var2_name],
            df[var_name],
            result["Slope"],
            result["Intercept"],
            var2_name,
            var_name,
        )
        if reg_chart:
            charts.append({"id": "reg-scatter", "title": reg_chart.pop("title"), **reg_chart})

    # Serialize chart config for Chart.js (type, data.labels, data.datasets, options)
    for c in charts:
        cfg = {
            "type": c.get("type", "line"),
            "data": {"labels": c.get("labels", []), "datasets": c.get("datasets", [])},
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "scales": {"x": {"display": True}, "y": {"display": True, "beginAtZero": c.get("type") == "bar"}},
            },
        }
        c["config_json"] = json.dumps(cfg)

    # Query string for export links (same analysis params)
    export_query = request.GET.urlencode() or request.META.get("QUERY_STRING", "")

    return render(
        request,
        "dataanalysis/analytics_result.html",
        {
            "dataset": dataset,
            "analysis": analysis,
            "result": result,
            "result_type": result_type,
            "variable": var_name,
            "variable2": var2_name,
            "charts": charts,
            "export_query": export_query,
        },
    )


@login_required
def export_analytics_pdf(request, pk):
    """Export current analysis result as PDF. GET params must match run_analytics (analysis, variable, etc.)."""
    dataset = get_object_or_404(Datasets, pk=pk, owner=request.user)
    df = get_dataset_dataframe(dataset)
    if df.empty:
        messages.warning(request, "No data in this dataset.")
        return redirect("dataanalysis:dataset_detail", pk=pk)
    form = AnalyticsForm(request.GET)
    if not form.is_valid():
        messages.warning(request, "Invalid parameters for export.")
        return redirect("dataanalysis:dataset_detail", pk=pk)
    analysis = form.cleaned_data["analysis"]
    var_name = form.cleaned_data.get("variable") or request.GET.get("variable")
    var2_name = form.cleaned_data.get("variable2") or request.GET.get("variable2")
    subgroup_size = form.cleaned_data.get("subgroup_size") or 5
    usl, lsl = form.cleaned_data.get("usl"), form.cleaned_data.get("lsl")
    mu0 = form.cleaned_data.get("mu0")
    result, result_type = _run_analysis(df, analysis, var_name, var2_name, subgroup_size, usl, lsl, mu0)
    if result is None:
        messages.warning(request, "Could not run analysis for export.")
        return redirect("dataanalysis:dataset_detail", pk=pk)
    analysis_label = dict(AnalyticsForm.ANALYSIS_CHOICES).get(analysis, analysis.replace("_", " ").title())
    try:
        chart_images = build_chart_images(
            analysis, result, result_type, df,
            var_name, var2_name,
            usl=usl, lsl=lsl,
        )
        pdf_bytes = build_pdf(
            dataset.name,
            analysis_label,
            result,
            result_type,
            variable=var_name,
            variable2=var2_name,
            chart_images=chart_images,
        )
    except ImportError:
        messages.warning(request, "PDF export requires the reportlab package. Install with: pip install reportlab")
        url = reverse("dataanalysis:run_analytics", kwargs={"pk": pk})
        if request.GET:
            url += "?" + request.GET.urlencode()
        return redirect(url)
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="analytics_report_{dataset.name}_{analysis}.pdf"'
    return resp


@login_required
def export_analytics_txt(request, pk):
    """Export session-style text output. GET params must match run_analytics."""
    dataset = get_object_or_404(Datasets, pk=pk, owner=request.user)
    df = get_dataset_dataframe(dataset)
    if df.empty:
        messages.warning(request, "No data in this dataset.")
        return redirect("dataanalysis:dataset_detail", pk=pk)
    form = AnalyticsForm(request.GET)
    if not form.is_valid():
        messages.warning(request, "Invalid parameters for export.")
        return redirect("dataanalysis:dataset_detail", pk=pk)
    analysis = form.cleaned_data["analysis"]
    var_name = form.cleaned_data.get("variable") or request.GET.get("variable")
    var2_name = form.cleaned_data.get("variable2") or request.GET.get("variable2")
    subgroup_size = form.cleaned_data.get("subgroup_size") or 5
    usl, lsl = form.cleaned_data.get("usl"), form.cleaned_data.get("lsl")
    mu0 = form.cleaned_data.get("mu0")
    result, result_type = _run_analysis(df, analysis, var_name, var2_name, subgroup_size, usl, lsl, mu0)
    if result is None:
        messages.warning(request, "Could not run analysis for export.")
        return redirect("dataanalysis:dataset_detail", pk=pk)
    analysis_label = dict(AnalyticsForm.ANALYSIS_CHOICES).get(analysis, analysis.replace("_", " ").title())
    text = build_session_txt(
        dataset.name,
        analysis_label,
        result,
        result_type,
        variable=var_name,
        variable2=var2_name,
    )
    resp = HttpResponse(text, content_type="text/plain; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="session_output_{dataset.name}_{analysis}.txt"'
    return resp
