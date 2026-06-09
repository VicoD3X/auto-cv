from autocv.engine.contracts import EngineRequest, EngineResponse


class PublicEngineStub:
    def generate(self, request: EngineRequest) -> EngineResponse:
        return EngineResponse(
            text=(
                "Le moteur privé Auto-CV n'est pas disponible dans cette version publique. "
                "Le logiciel peut démarrer, mais la génération avancée reste désactivée."
            ),
            source="public_stub",
            available=False,
        )

