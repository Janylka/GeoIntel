import os
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def generate_report_pdf(
    customer_name: str, metrics: dict[str, Any], explanation: str, output_path: str
) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(
        200, 10, text=f"GeoIntel Report for {customer_name}",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C",
    )

    pdf.set_font("Helvetica", size=12)
    pdf.ln(10)
    for k, v in metrics.items():
        pdf.cell(200, 8, text=f"{k}: {v}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(10)
    pdf.multi_cell(0, 8, text=explanation)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    return output_path
