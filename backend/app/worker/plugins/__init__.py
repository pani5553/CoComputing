"""
Plugin registry for worker task types.
To add a new type: create the plugin module, import it here, and register it.
"""
from app.worker.plugins.data_processing import DataProcessingPlugin

PLUGINS: dict[str, type] = {
    DataProcessingPlugin.job_type: DataProcessingPlugin,
}


def get_plugin(job_type: str):
    """Return an instantiated plugin for job_type, or None if unsupported."""
    cls = PLUGINS.get(job_type)
    return cls() if cls else None
