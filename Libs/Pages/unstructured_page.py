from dataclasses import dataclass
from Libs.Pages.page import Page


@dataclass
class UnstructuredPage(Page):
    """
    Ham Sinyal. Henüz entegre edilmemiş girdi verisi.
    """

    predicted_output: str = ""
    prediction_error: float = 0.0
