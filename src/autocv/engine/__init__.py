"""Public engine contracts and safe fallback implementation."""

from autocv.engine.contracts import AutoCvEngine, EngineRequest, EngineResponse
from autocv.engine.loader import load_engine

__all__ = [
    "AutoCvEngine",
    "EngineRequest",
    "EngineResponse",
    "load_engine",
]

