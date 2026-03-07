import pandas as pd
from pathlib import Path
from dataanalysis.models import DatasetFile, Variables


def process_uploaded_file(dataset_file: DatasetFile):
    file_path = dataset_file.file.path
    path = Path(file_path)
    suffix = path.suffix.lower()

    if dataset_file.file_type == "csv" or suffix == ".csv":
        df = pd.read_csv(file_path)
    elif dataset_file.file_type == "xlsx" or suffix in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported file type: {dataset_file.file_type or suffix}")

    # Save metadata
    dataset_file.row_count = len(df)
    dataset_file.column_count = len(df.columns)

    # Convert to parquet for fast analytics
    parquet_path = path.with_suffix(".parquet")
    df.to_parquet(parquet_path, index=False)

    # Store relative path for FileField (relative to MEDIA_ROOT)
    dataset_file.file.name = str(Path(dataset_file.file.name).with_suffix(".parquet")).replace("\\", "/")
    dataset_file.file_type = "parquet"
    dataset_file.save(update_fields=["row_count", "column_count", "file", "file_type"])

    # Auto detect variables
    create_variables_from_dataframe(dataset_file.dataset, df)

def detect_type(series):
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    
    unique_ratio = series.nunique() / len(series)

    if unique_ratio < 0.05:
        return "categorical"
    
    return "text"

def create_variables_from_dataframe(dataset, df):
    Variables.objects.filter(dataset=dataset).delete()
    for column in df.columns:
        dtype = detect_type(df[column])
        Variables.objects.create(
            dataset=dataset,
            name=column,
            data_type=dtype
        )


def get_dataset_dataframe(dataset):
    """
    Load all data for a dataset into one DataFrame: uploaded file(s) + manual records.
    """
    from dataanalysis.models import ManualRecord

    dfs = []

    # From uploaded parquet files
    for f in dataset.files.filter(file_type="parquet"):
        if f.file and hasattr(f.file, "path"):
            try:
                df = pd.read_parquet(f.file.path)
                dfs.append(df)
            except Exception:
                pass

    # From manual records
    records = list(dataset.manual_records.all())
    if records:
        manual_df = pd.DataFrame([r.values for r in records])
        if not manual_df.empty:
            dfs.append(manual_df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)