import re

from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


PLACEHOLDER_DATES = "FECHAS PENDIENTES"
PLACEHOLDER_CENTER = "Alejandro2000"
PLACEHOLDER_ADDRESS = "C/ Falsa 123, 38320 Santa Cruz de Tenerife"
PLACEHOLDER_LOCALITY = "Reino de la Piruleta"
PROVINCE = "Santa Cruz de Tenerife"
ACTION_CODE = "24-38/001234"
ANEXO_FONT_SIZE = 10
HEADER_ROW_HEIGHT_CM = 1.7


def module_code(text):
    match = re.search(r"\b(?:MF\d{4}_\d|MP\d{4})\b", text)
    return match.group(0) if match else ""


def hours_from_text(text):
    found = re.findall(r"\((\d+)\s*horas?\)", text, flags=re.IGNORECASE)
    return found[-1] if found else ""


def title_without_hours(text):
    return re.sub(r"\s*\(\d+\s*horas?\)\s*$", "", text, flags=re.IGNORECASE).strip()


def duration_for_anexo(duration_text):
    match = re.match(r"^(\d+)h\s*\+\s*(\d+)h\s*FEM$", duration_text, flags=re.IGNORECASE)

    if match:
        mf_hours = int(match.group(1))
        mp_hours = int(match.group(2))
        return f"{mf_hours} + {mp_hours} FEM = {mf_hours + mp_hours} HORAS"

    match = re.match(r"^(\d+)h$", duration_text, flags=re.IGNORECASE)

    if match:
        return f"{match.group(1)} HORAS"

    return duration_text.upper()


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def set_cell_margins(cell, top=140, bottom=140):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")

    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)

    for margin_name, value in (("top", top), ("bottom", bottom)):
        margin = tc_mar.find(qn(f"w:{margin_name}"))

        if margin is None:
            margin = OxmlElement(f"w:{margin_name}")
            tc_mar.append(margin)

        margin.set(qn("w:w"), str(value))
        margin.set(qn("w:type"), "dxa")


def set_cell_text(
    cell,
    text,
    bold=False,
    size=ANEXO_FONT_SIZE,
    align=WD_ALIGN_PARAGRAPH.LEFT,
    vertical_padding=True
):
    cell.text = ""

    if vertical_padding:
        set_cell_margins(cell)

    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(str(text or ""))
    run.bold = bold
    run.font.size = Pt(size)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def set_header_cell(cell, text):
    set_cell_shading(cell, "4F81BD")
    set_cell_text(cell, text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, vertical_padding=False)

    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.font.color.rgb = RGBColor(255, 255, 255)


def add_label_value(paragraph, label, value):
    paragraph.paragraph_format.space_after = Pt(0)
    label_run = paragraph.add_run(label)
    label_run.bold = True
    label_run.font.size = Pt(ANEXO_FONT_SIZE)
    value_run = paragraph.add_run(value)
    value_run.font.size = Pt(ANEXO_FONT_SIZE)


def add_centered_heading(doc, text, bold=True):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.size = Pt(ANEXO_FONT_SIZE)
    return paragraph


def add_tabbed_label_line(doc, parts):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(0)

    tab_stops = paragraph.paragraph_format.tab_stops
    tab_stops.add_tab_stop(Inches(4.6))
    tab_stops.add_tab_stop(Inches(8.0))

    for index, (label, value) in enumerate(parts):
        if index:
            paragraph.add_run("\t")

        add_label_value(paragraph, label, value)

    return paragraph


def add_anexo_header(doc, data, duration_text):
    add_centered_heading(doc, "ANEXO III")
    add_centered_heading(doc, "Planificación didáctica")
    doc.add_paragraph("")

    certificate = (
        f"{ACTION_CODE} {data.get('codigo', '')} "
        f"{data.get('nombre', '').upper()}"
    ).strip()

    add_tabbed_label_line(doc, [
        ("CERTIFICADO DE PROFESIONALIDAD: ", certificate),
    ])
    add_tabbed_label_line(doc, [
        ("DURACIÓN DEL CERTIFICADO: ", duration_for_anexo(duration_text)),
        ("FECHAS DE IMPARTICIÓN: ", PLACEHOLDER_DATES),
    ])
    add_tabbed_label_line(doc, [
        ("CENTRO DE FORMACIÓN: ", PLACEHOLDER_CENTER),
    ])
    add_tabbed_label_line(doc, [
        ("DIRECCIÓN: ", PLACEHOLDER_ADDRESS),
        ("LOCALIDAD: ", PLACEHOLDER_LOCALITY),
        ("PROVINCIA: ", PROVINCE),
    ])


def module_rows(module):
    module_text = title_without_hours(module.get("text", ""))
    module_hours = hours_from_text(module.get("text", ""))
    ufs = module.get("ufs", [])

    if not ufs:
        return [{
            "module": module_text,
            "module_hours": module_hours,
            "uf": "",
            "uf_hours": "",
            "dates": "",
        }]

    rows = []

    for uf in ufs:
        rows.append({
            "module": module_text,
            "module_hours": module_hours,
            "uf": title_without_hours(uf),
            "uf_hours": hours_from_text(uf),
            "dates": "",
        })

    return rows


def add_planning_table(doc, modules):
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(8)
    title.paragraph_format.space_after = Pt(4)
    run = title.add_run("PLANIFICACIÓN DIDÁCTICA DEL CURSO COMPLETO")
    run.bold = True
    run.font.size = Pt(ANEXO_FONT_SIZE)

    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = False

    headers = [
        "MÓDULOS DEL CERTIFICADO",
        "HORAS\nDEL\nMÓDULO",
        "UNIDADES FORMATIVAS\n(UF)",
        "HORAS\n(UF)",
        "FECHAS DE IMPARTICIÓN",
    ]

    widths = [Inches(3.2), Inches(0.7), Inches(3.6), Inches(0.65), Inches(1.8)]

    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        set_header_cell(cell, header)
        cell.width = widths[index]

    table.rows[0].height = Cm(HEADER_ROW_HEIGHT_CM)

    for module in modules:
        rows = module_rows(module)
        first_row_index = len(table.rows)

        for row_data in rows:
            cells = table.add_row().cells
            is_first_module_row = len(table.rows) - 1 == first_row_index
            values = [
                row_data["module"] if is_first_module_row else "",
                row_data["module_hours"] if is_first_module_row else "",
                row_data["uf"],
                row_data["uf_hours"],
                row_data["dates"],
            ]

            for index, value in enumerate(values):
                set_cell_text(
                    cells[index],
                    value,
                    size=ANEXO_FONT_SIZE,
                    align=WD_ALIGN_PARAGRAPH.CENTER if index in (1, 3, 4) else WD_ALIGN_PARAGRAPH.LEFT
                )
                cells[index].width = widths[index]

        if len(rows) > 1:
            last_row_index = len(table.rows) - 1
            module_cell = table.cell(first_row_index, 0).merge(table.cell(last_row_index, 0))
            hours_cell = table.cell(first_row_index, 1).merge(table.cell(last_row_index, 1))
            set_cell_text(module_cell, rows[0]["module"], size=ANEXO_FONT_SIZE)
            set_cell_text(hours_cell, rows[0]["module_hours"], size=ANEXO_FONT_SIZE, align=WD_ALIGN_PARAGRAPH.CENTER)

    return table


def add_anexo_iii(doc, data, modules, duration_text):
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.top_margin = Inches(0.45)
    section.bottom_margin = Inches(0.45)
    section.left_margin = Inches(0.45)
    section.right_margin = Inches(0.45)

    add_anexo_header(doc, data, duration_text)
    add_planning_table(doc, modules)
