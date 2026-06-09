from autocv.conversion.contracts import ConversionRequest, ConversionResponse


class PublicConversionStub:
    def convert(self, request: ConversionRequest) -> ConversionResponse:
        return ConversionResponse(
            output_path=request.output_path,
            source="public_stub",
            available=False,
            message=(
                "Le moteur privé de conversion documentaire n'est pas disponible "
                "dans cette version publique."
            ),
        )

