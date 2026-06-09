from autocv.i18n.fr_fr import APPLICATION_STATUS_LABELS, APP_LABELS, DEFAULT_LOCALE


def test_product_defaults_to_french() -> None:
    assert DEFAULT_LOCALE == "fr-FR"
    assert APP_LABELS["app_ready"] == "Auto-CV prêt"
    assert APPLICATION_STATUS_LABELS["ready"] == "Prêt à envoyer"
