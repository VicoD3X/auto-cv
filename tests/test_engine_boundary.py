from autocv.engine import EngineRequest, load_engine


def test_public_engine_falls_back_to_stub_when_private_engine_is_absent() -> None:
    engine = load_engine("autocv_private_engine_missing_for_test")

    response = engine.generate(
        EngineRequest(
            task="cover_letter_draft",
            content="Offre Data Scientist",
        )
    )

    assert response.available is False
    assert response.source == "public_stub"
    assert "moteur privé" in response.text
