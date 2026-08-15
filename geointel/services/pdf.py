import os
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# fpdf2's core fonts (Helvetica, Times, ...) only cover latin-1 and cannot render
# Cyrillic, let alone the Kyrgyz-specific letters (ң, ө, ү). Noto Sans covers all
# three languages GeoIntel reports are generated in (ru, ky, en), so it's embedded
# and used for the whole document instead.
_FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_FONT_NAME = "NotoSans"


def _register_font(pdf: FPDF) -> None:
    pdf.add_font(_FONT_NAME, "", os.path.join(_FONTS_DIR, "NotoSans-Regular.ttf"))
    pdf.add_font(_FONT_NAME, "B", os.path.join(_FONTS_DIR, "NotoSans-Bold.ttf"))


def generate_report_pdf(
    customer_name: str, metrics: dict[str, Any], explanation: str, output_path: str
) -> str:
    pdf = FPDF()
    _register_font(pdf)
    pdf.add_page()
    pdf.set_font(_FONT_NAME, style="B", size=16)
    pdf.cell(
        200, 10, text=f"GeoIntel Report for {customer_name}",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C",
    )

    pdf.set_font(_FONT_NAME, size=12)
    pdf.ln(10)
    for k, v in metrics.items():
        pdf.cell(200, 8, text=f"{k}: {v}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(10)
    pdf.multi_cell(0, 8, text=explanation)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    return output_path
