"""
Data processing plugin for the worker.

Uses polars if available, falls back to statistics module (pure stdlib).
Accepts payload: {"rows": [[...]], "columns": [...], "operation": str, "target_columns": [...]}
Returns: {"<col>_<operation>": value, ...}
"""
import logging
from typing import Any

from app.worker.plugins.base import WorkerPlugin

logger = logging.getLogger(__name__)


def _try_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class DataProcessingPlugin(WorkerPlugin):
    job_type = "data-processing"

    def process(self, payload: dict) -> dict:
        rows: list[list] = payload.get("rows", [])
        columns: list[str] = payload.get("columns", [])
        operation: str = payload.get("operation", "mean")
        target_columns: list[str] = payload.get("target_columns", columns)

        if not rows or not columns:
            return {}

        try:
            return self._process_with_polars(rows, columns, operation, target_columns)
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("polars falló, usando stdlib: %s", exc)

        return self._process_stdlib(rows, columns, operation, target_columns)

    def _process_with_polars(
        self,
        rows: list,
        columns: list[str],
        operation: str,
        target_columns: list[str],
    ) -> dict:
        import polars as pl

        df = pl.DataFrame(data=rows, schema=columns, orient="row")
        result: dict[str, Any] = {}

        for col in target_columns:
            if col not in df.columns:
                continue
            try:
                series = df[col].cast(pl.Float64, strict=False).drop_nulls()
            except Exception:
                continue
            if series.is_empty():
                continue

            if operation == "mean":
                val = series.mean()
            elif operation == "sum":
                val = series.sum()
            elif operation == "min":
                val = series.min()
            elif operation == "max":
                val = series.max()
            elif operation == "count":
                val = series.len()
            else:
                val = series.mean()

            result[f"{col}_{operation}"] = round(float(val), 6) if val is not None else None

        return result

    def _process_stdlib(
        self,
        rows: list,
        columns: list[str],
        operation: str,
        target_columns: list[str],
    ) -> dict:
        import statistics

        # Build column index map
        col_index = {col: idx for idx, col in enumerate(columns)}
        result: dict[str, Any] = {}

        for col in target_columns:
            idx = col_index.get(col)
            if idx is None:
                continue
            values = [_try_float(row[idx]) for row in rows if idx < len(row)]
            values = [v for v in values if v is not None]
            if not values:
                continue

            if operation == "mean":
                val = statistics.mean(values)
            elif operation == "sum":
                val = sum(values)
            elif operation == "min":
                val = min(values)
            elif operation == "max":
                val = max(values)
            elif operation == "count":
                val = float(len(values))
            else:
                val = statistics.mean(values)

            result[f"{col}_{operation}"] = round(val, 6)

        return result
