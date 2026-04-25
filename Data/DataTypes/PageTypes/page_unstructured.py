from pydantic import Field
from Data.DataTypes.PageTypes.page import Page


class UnstructuredPage(Page):
    """
    Ham Sinyal (Zettelkasten: Fleeting Note).
    Henüz entegre edilmemiş, rdf ağına dökülmemiş girdi verisi.
    """

    predicted_output: str = ""
    prediction_error: float = 0.0
    keywords: list[str] = Field(default_factory=list)

    @property
    def is_high_diff_err(self) -> bool:
        """Hata > 0.7 ise bu veri ayrı bir işlem gerektirir"""
        return self.prediction_error > 0.7
