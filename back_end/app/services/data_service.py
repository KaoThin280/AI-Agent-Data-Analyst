# app/services/data_service.py
import os
import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

BUSINESS_HINTS = {
    "id": "Identifier",
    "date": "Date / Timestamp",
    "time": "Time",
    "amount": "Monetary amount",
    "price": "Price",
    "cost": "Cost",
    "revenue": "Revenue",
    "profit": "Profit",
    "quantity": "Quantity / Count",
    "count": "Count",
    "name": "Name / Label",
    "description": "Description",
    "address": "Address",
    "email": "Email",
    "phone": "Phone number",
    "category": "Category",
    "type": "Type / Category",
    "status": "Status",
    "flag": "Flag / Indicator",
    "score": "Score / Rating",
    "rate": "Rate",
    "percentage": "Percentage",
    "ratio": "Ratio",
    "age": "Age",
    "year": "Year",
    "month": "Month",
    "day": "Day",
    "lat": "Latitude",
    "lon": "Longitude",
    "longitude": "Longitude",
    "latitude": "Latitude",
    "url": "URL",
    "file": "File path",
    "image": "Image path",
    "comment": "Comment / Note",
    "note": "Note",
    "location": "Location",
}


def _infer_meaning(column_name: str) -> str:
    name_lower = column_name.lower().strip()
    if name_lower in BUSINESS_HINTS:
        return BUSINESS_HINTS[name_lower]
    for key, meaning in BUSINESS_HINTS.items():
        if key in name_lower or name_lower.endswith(key) or name_lower.startswith(key):
            return meaning
    return "Unknown / Generic"


class DataContext:
    """Holds all extracted information about an uploaded tabular file."""

    def __init__(
        self,
        file_name: str,
        num_rows: int,
        num_columns: int,
        columns: Dict[str, Dict[str, Any]],
        stats: Dict[str, Any],
        head: List[Dict[str, Any]],
        tail: List[Dict[str, Any]],
        missing_info: Dict[str, Dict[str, Any]],
    ):
        self.file_name = file_name
        self.num_rows = num_rows
        self.num_columns = num_columns
        self.columns = columns
        self.stats = stats
        self.head = head
        self.tail = tail
        self.missing_info = missing_info

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "num_rows": self.num_rows,
            "num_columns": self.num_columns,
            "columns": self.columns,
            "stats": self.stats,
            "head": self.head,
            "tail": self.tail,
            "missing_info": self.missing_info,
        }

    def to_summary(self) -> str:
        lines = [
            f"File: {self.file_name}",
            f"Rows: {self.num_rows}, Columns: {self.num_columns}",
            "",
            "Columns:",
        ]
        for col_name, col_info in self.columns.items():
            dtype = col_info.get("dtype", "unknown")
            meaning = col_info.get("business_meaning", "Unknown")
            lines.append(f"  - {col_name} ({dtype}, {meaning})")

        if self.stats:
            lines.append("")
            lines.append("Descriptive statistics (numeric columns):")
            for col, stats_dict in self.stats.items():
                stats_line = ", ".join(
                    f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                    for k, v in stats_dict.items()
                )
                lines.append(f"  {col}: {stats_line}")

        if self.missing_info:
            lines.append("")
            lines.append("Missing values:")
            for col, miss in self.missing_info.items():
                if miss["missing_count"] > 0:
                    lines.append(
                        f"  {col}: {miss['missing_count']} missing "
                        f"({miss['missing_percentage']}%)"
                    )

        lines.append("")
        lines.append("First 4 rows:")
        for row in self.head[:2]:
            lines.append(f"  {list(row.values())[:5]}...")
        lines.append("")
        lines.append("Last 4 rows:")
        for row in self.tail[:2]:
            lines.append(f"  {list(row.values())[:5]}...")

        return "\n".join(lines)


class DataProcessor:
    """Processes uploaded tabular files in a memory-efficient manner."""

    @staticmethod
    def extract_data_context(file_path: str) -> DataContext:
        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_name)[1].lower()

        logger.info("Processing file: %s", file_name)

        try:
            if ext == ".csv":
                use_pyarrow = False
                try:
                    import pyarrow
                    use_pyarrow = True
                except ImportError:
                    pass

                if use_pyarrow:
                    df = pd.read_csv(
                        file_path,
                        dtype_backend="pyarrow",
                        engine="pyarrow",
                    )
                else:
                    df = pd.read_csv(
                        file_path,
                        engine="c",
                        low_memory=False,
                    )
            elif ext in (".xls", ".xlsx"):
                df = pd.read_excel(file_path, engine="openpyxl")
            else:
                raise ValueError(
                    f"Unsupported file extension: {ext}. Only CSV and Excel are allowed."
                )
        except Exception as e:
            logger.error("Failed to read file '%s': %s", file_name, str(e))
            raise ValueError(f"Could not read file: {e}")

        logger.info("Loaded %d rows and %d columns", len(df), len(df.columns))

        num_rows, num_columns = df.shape
        columns_info: Dict[str, Dict[str, Any]] = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            meaning = _infer_meaning(col)
            columns_info[col] = {
                "dtype": dtype,
                "business_meaning": meaning,
            }

        stats = {}
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            desc = df[numeric_cols].describe(
                percentiles=[0.25, 0.5, 0.75], include="number"
            )
            stats = desc.to_dict()
        else:
            logger.info("No numeric columns found, statistics omitted.")

        head_rows = df.head(4).to_dict(orient="records")
        tail_rows = df.tail(4).to_dict(orient="records")

        missing_info: Dict[str, Dict[str, Any]] = {}
        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            null_pct = round((null_count / num_rows) * 100, 2) if num_rows > 0 else 0.0
            missing_info[col] = {
                "missing_count": null_count,
                "missing_percentage": null_pct,
            }

        context = DataContext(
            file_name=file_name,
            num_rows=num_rows,
            num_columns=num_columns,
            columns=columns_info,
            stats=stats,
            head=head_rows,
            tail=tail_rows,
            missing_info=missing_info,
        )

        del df
        logger.info("Data context extracted successfully for '%s'", file_name)

        return context