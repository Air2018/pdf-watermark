import subprocess
from typing import Tuple
from reportlab.pdfgen import canvas
from math import cos, sin, pi
import numpy as np
from app.objects import DrawingOptions, UserInputs
import PyPDF4
from tempfile import NamedTemporaryFile
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from matplotlib import font_manager

def draw_centered_image(
    canvas: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    image: ImageReader,
):
    bottom_left_x = x - width / 2
    bottom_left_y = y - height / 2
    canvas.drawImage(
        image,
        bottom_left_x,
        bottom_left_y,
        width=width,
        height=height,
        mask="auto",
    )


def change_base(x: float, y: float, rotation_matrix: np.ndarray) -> Tuple[float, float]:
    # Since we rotated the original coordinates system, use the inverse of the rotation matrix
    # (which is the transposed matrix) to get the coordinates we have to draw at
    new_coordinates = np.transpose(rotation_matrix) @ np.array([[x], [y]])
    return new_coordinates[0, 0], new_coordinates[1, 0]


def create_watermark_pdf(
    file_name: str, width: float, height: float, drawing_options: DrawingOptions
):
    watermark = canvas.Canvas(file_name, pagesize=(width, height))

    horizontal_box_spacing = width / drawing_options.horizontal_boxes
    vertical_box_spacing = height / drawing_options.vertical_boxes

    rotation_angle_rad = drawing_options.angle * pi / 180
    rotation_matrix = np.array(
        [
            [cos(rotation_angle_rad), -sin(rotation_angle_rad)],
            [sin(rotation_angle_rad), cos(rotation_angle_rad)],
        ]
    )

    if drawing_options.text is not None and is_chinese(str(drawing_options.text)):
        fonts = watermark.getAvailableFonts()
        # print("watermark is Chinese. {}".format(drawing_options.text_font))
        zh_fonts = get_all_zh_font()
        if zh_fonts is not None and len(zh_fonts) > 0:
            zh_font = drawing_options.text_font
            if zh_font not in zh_fonts:
                zh_font = zh_fonts[0]
                
            pdfmetrics.registerFont(TTFont(zh_font, font_manager.findfont(zh_font)))
            drawing_options.text_font = zh_font
        else:
            print("Please install Chinese font.")

    watermark.setFillColor(drawing_options.text_color, alpha=drawing_options.opacity)
    watermark.setFont(drawing_options.text_font, drawing_options.text_size)
    watermark.rotate(drawing_options.angle)

    if drawing_options.margin:
        start_index = 1
    else:
        start_index = 0

    for x_index in range(start_index, drawing_options.horizontal_boxes + 1):
        for y_index in range(start_index, drawing_options.vertical_boxes + 1):
            # Coordinates to draw at in original coordinates system
            x_base = x_index * horizontal_box_spacing
            y_base = y_index * vertical_box_spacing

            if drawing_options.margin:
                x_base -= horizontal_box_spacing / 2
                y_base -= vertical_box_spacing / 2

            x_prime, y_prime = change_base(x_base, y_base, rotation_matrix)

            if drawing_options.text is not None:
                watermark.drawCentredString(
                    x_prime,
                    y_prime,
                    drawing_options.text,
                )

            if drawing_options.image is not None:
                # if the image is too big, scale it down to fit in the box
                image_width, image_height = drawing_options.image.getSize()
                if image_width > horizontal_box_spacing:
                    change_ratio = horizontal_box_spacing / image_width
                    image_width = horizontal_box_spacing
                    image_height *= change_ratio
                if image_height > vertical_box_spacing:
                    change_ratio = vertical_box_spacing / image_height
                    image_height = vertical_box_spacing
                    image_width *= change_ratio

                image_width *= drawing_options.image_scale
                image_height *= drawing_options.image_scale

                draw_centered_image(
                    watermark,
                    x_prime,
                    y_prime,
                    image_width,
                    image_height,
                    drawing_options.image,
                )

    watermark.save()

def is_chinese(text: str):
    """
    Check whether the entire string contains Chinese
    """
    for ch in text:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False

def get_all_zh_font():
    fm = font_manager.FontManager()
    ttf_fonts = set(f.name for f in fm.ttflist)
    output = subprocess.check_output('fc-list :lang=zh -f "%{family}\n"', shell=True)
    zh_fonts = set(f.split(',', 1)[0] for f in output.decode().split('\n'))
    available = list(ttf_fonts & zh_fonts)

    # print('*' * 10, 'available Chinese fonts:', '*' * 10)
    # for f in available:
    #     print(f)
    return available

def add_watermark_to_pdf(input: str, output: str, drawing_options: DrawingOptions):
    pdf_to_transform = PyPDF4.PdfFileReader(input)
    pdf_box = pdf_to_transform.pages[0].mediaBox
    page_width = float(pdf_box.getWidth())
    page_height = float(pdf_box.getHeight())

    with NamedTemporaryFile() as temporary_file:
        # The watermark is stored in a temporary pdf file
        create_watermark_pdf(
            temporary_file.name,
            page_width,
            page_height,
            drawing_options,
        )

        watermark_pdf = PyPDF4.PdfFileReader(temporary_file.name)
        pdf_writer = PyPDF4.PdfFileWriter()

        for page in pdf_to_transform.pages:
            page.mergePage(watermark_pdf.pages[0])
            pdf_writer.addPage(page)

    with open(output, "wb") as f:
        pdf_writer.write(f)


def add_watermark_from_inputs(inputs: UserInputs):
    for input_file, output_file in inputs.files_options:
        add_watermark_to_pdf(input_file, output_file, inputs.drawing_options)
