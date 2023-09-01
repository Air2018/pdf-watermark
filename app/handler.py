from typing import Union
from app.options import (
    DrawingOptions,
    FilesOptions,
    GridOptions,
    InsertOptions,
)
import PyPDF4
from tempfile import NamedTemporaryFile

from app.draw import draw_watermarks


def add_watermark_to_pdf(
    input: str,
    output: str,
    drawing_options: DrawingOptions,
    specific_options: Union[GridOptions, InsertOptions],
):
    pdf_to_transform = PyPDF4.PdfFileReader(input)
    pdf_box = pdf_to_transform.pages[0].mediaBox
    page_width = float(pdf_box.getWidth())
    page_height = float(pdf_box.getHeight())

    with NamedTemporaryFile() as temporary_file:
        # The watermark is stored in a temporary pdf file
        draw_watermarks(
            temporary_file.name,
            page_width,
            page_height,
            drawing_options,
            specific_options,
        )

        watermark_pdf = PyPDF4.PdfFileReader(temporary_file.name)
        pdf_writer = PyPDF4.PdfFileWriter()

        for page in pdf_to_transform.pages:
            page.mergePage(watermark_pdf.pages[0])
            pdf_writer.addPage(page)

    with open(output, "wb") as f:
        pdf_writer.write(f)


def add_watermark_from_options(
    files_options: FilesOptions,
    drawing_options: DrawingOptions,
    specific_options: Union[GridOptions, InsertOptions],
):
    for input_file, output_file in files_options:
        add_watermark_to_pdf(input_file, output_file, drawing_options, specific_options)
