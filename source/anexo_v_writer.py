from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Cm, Pt

from source.anexo_iv_writer import (
    add_horizontal_line,
    add_module_header,
    configure_page,
    module_identifier_without_hours,
)
from source.docx_styles import (
    ANEXO_IV_FONT_SIZE,
    ANEXO_IV_TABLE_HEADER_FILL,
    ANEXO_IV_TABLE_WIDTH_PERCENT,
    LIGHT_BORDER,
)
from source.settings import DEFAULT_TEACHER_NAME
from source.table_styles import (
    apply_vertical_borders,
    set_cell_shading,
    set_cell_text,
    set_table_width_percent,
)


def build_anexo_v_filename(module_code, certificate_code):
    return f"anexoV_{module_code}_{certificate_code}.docx"


def block_label(block):
    code = getattr(block, "code", "")
    name = getattr(block, "name", "")

    if code or name:
        return f"{code}: {name}".strip(": ")

    return module_identifier_without_hours(block)


def evaluation_blocks(module):
    return module.ufs or [module]


def add_anexo_v_table(doc, module):
    add_horizontal_line(doc)

    table = doc.add_table(rows=2, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = False
    set_table_width_percent(table, ANEXO_IV_TABLE_WIDTH_PERCENT)

    widths = [Cm(3.1), Cm(6.1), Cm(2.4), Cm(1.8), Cm(2.4)]

    for row in table.rows:
        for index, cell in enumerate(row.cells):
            cell.width = widths[index]
            set_cell_shading(cell, ANEXO_IV_TABLE_HEADER_FILL)

    evaluation_header = table.cell(0, 2).merge(table.cell(0, 4))

    set_cell_text(table.cell(0, 0), "MÓDULO\nPROFESIONAL", size=ANEXO_IV_FONT_SIZE)
    set_cell_text(table.cell(1, 0), "BLOQUES\nFORMATIVOS", size=ANEXO_IV_FONT_SIZE)
    set_cell_text(table.cell(0, 1), "DURANTE EL PROCESO DE\nAPRENDIZAJE", size=ANEXO_IV_FONT_SIZE)
    set_cell_text(table.cell(1, 1), "ACTIVIDADES E INSTRUMENTOS\nDE EVALUACIÓN¹", size=ANEXO_IV_FONT_SIZE)
    set_cell_text(
        evaluation_header,
        "Realización de la evaluación",
        size=ANEXO_IV_FONT_SIZE,
    )

    subheaders = ["Espacios", "Duración", "Fechas de\nevaluación²"]

    for offset, header in enumerate(subheaders, start=2):
        cell = table.rows[1].cells[offset]
        set_cell_shading(cell, ANEXO_IV_TABLE_HEADER_FILL)
        set_cell_text(cell, header, size=ANEXO_IV_FONT_SIZE)
        cell.width = widths[offset]

    for block in evaluation_blocks(module):
        cells = table.add_row().cells

        for index, cell in enumerate(cells):
            cell.width = widths[index]

        set_cell_text(cells[0], block_label(block), size=ANEXO_IV_FONT_SIZE)

        for cell in cells[1:]:
            set_cell_text(cell, "", size=ANEXO_IV_FONT_SIZE)

    apply_vertical_borders(table, LIGHT_BORDER)
    return table


def add_anexo_v_notes(doc):
    notes = [
        (
            "1 Identificar las actividades e instrumentos de evaluación (E.; E.; etc.) "
            "indicando una denominación sintética de los mismos (supuestos prácticos, "
            "simulaciones, pruebas objetivas y/o pruebas de respuesta abierta)."
        ),
        (
            "2 Las fechas de evaluación estarán actualizadas en el momento en el que "
            "se efectúe la comunicación de inicio de las acciones formativas a la "
            "administración competente."
        ),
    ]

    for note in notes:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(note)
        run.font.size = Pt(ANEXO_IV_FONT_SIZE)


def create_anexo_v_docx(
    data,
    module,
    duration_text,
    output_path,
    schedule=None,
    add_header_footer=None,
    teacher_name=DEFAULT_TEACHER_NAME,
):
    doc = Document()
    configure_page(doc.sections[0])

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(ANEXO_IV_FONT_SIZE)

    add_module_header(
        doc,
        data,
        module,
        duration_text,
        schedule,
        annex_label="ANEXO V",
        document_title="Planificación de la evaluación del aprendizaje",
        module_section_title="PLANIFICACIÓN DE LA EVALUACIÓN DEL APRENDIZAJE",
    )
    add_anexo_v_table(doc, module)
    add_anexo_v_notes(doc)

    if add_header_footer is None:
        from source.docx_utils import add_header_footer

    add_header_footer(doc, teacher_name)

    doc.save(output_path)
