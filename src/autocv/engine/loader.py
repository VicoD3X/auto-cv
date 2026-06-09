from importlib import import_module

from autocv.engine.contracts import AutoCvEngine
from autocv.engine.public_stub import PublicEngineStub


def load_engine(module_name: str = "autocv_private_engine") -> AutoCvEngine:
    try:
        private_engine_module = import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        return PublicEngineStub()

    create_engine = getattr(private_engine_module, "create_engine", None)
    if create_engine is None:
        return PublicEngineStub()

    return create_engine()
