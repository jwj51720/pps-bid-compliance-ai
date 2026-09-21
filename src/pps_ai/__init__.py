"""Clean-room PPS compliance pipeline.

This package must not import the historical ``src.*`` pipeline.  Frozen
reference implementations are loaded only through a hash-pinned adapter.
"""

from .config import CleanExperimentConfig, load_experiment_config

__all__ = ["CleanExperimentConfig", "load_experiment_config"]
