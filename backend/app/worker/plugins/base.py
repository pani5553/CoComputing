"""
Abstract base class for worker plugins.
Each plugin handles one job_type and exposes a single process() method.
"""
from abc import ABC, abstractmethod


class WorkerPlugin(ABC):
    job_type: str  # class-level attribute, e.g. "data-processing"

    @abstractmethod
    def process(self, payload: dict) -> dict:
        """
        Process a single chunk payload and return the result dict.

        payload format for data-processing:
          {
            "rows": [[val, val, ...], ...],
            "columns": ["col1", "col2", ...],
            "operation": "mean" | "sum" | "min" | "max" | "count",
            "target_columns": ["col1", ...]
          }

        Returns:
          {"<col>_<operation>": value, ...}
        """
