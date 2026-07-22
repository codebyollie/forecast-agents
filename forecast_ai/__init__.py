"""
Forecast AI

Open-source Multi-Agent Intelligence Infrastructure for Prediction Markets.
"""

__version__ = "0.1.0"

from .config import ForecastConfig
from .launcher import ForecastLauncher
from .config_store import ConfigStore

__all__ = [
    "ForecastConfig",
    "ForecastLauncher",
    "ConfigStore",
]