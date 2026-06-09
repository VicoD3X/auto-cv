from autocv.engine.contracts import EngineRequest, EngineResponse
from autocv.ai import QWEN3_14B_Q4_PROFILE


class PublicEngineStub:
    def generate(self, request: EngineRequest) -> EngineResponse:
        return EngineResponse(
            text=(
                "Le moteur privé Auto-CV n'est pas disponible dans cette version publique. "
                "Le logiciel peut démarrer, mais la génération avancée reste désactivée."
            ),
            source="public_stub",
            available=False,
            model=QWEN3_14B_Q4_PROFILE.default_model_ref,
        )
