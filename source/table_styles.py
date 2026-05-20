from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def set_table_width_percent(table, percent):
    table_pr = table._tbl.tblPr
    tbl_w = table_pr.find(qn("w:tblW"))

    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        table_pr.append(tbl_w)

    tbl_w.set(qn("w:w"), str(percent * 50))
    tbl_w.set(qn("w:type"), "pct")


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
    *,
    bold=False,
    size=10,
    align=WD_ALIGN_PARAGRAPH.LEFT,
    vertical_alignment=WD_ALIGN_VERTICAL.CENTER,
    vertical_padding=False,
    margin_top=140,
    margin_bottom=140,
):
    cell.text = ""
    cell.vertical_alignment = vertical_alignment

    if vertical_padding:
        set_cell_margins(cell, top=margin_top, bottom=margin_bottom)

    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(str(text or ""))
    run.bold = bold
    run.font.size = Pt(size)


def set_cell_vertical_borders(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")

    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)

    for border_name in ("left", "right"):
        border = borders.find(qn(f"w:{border_name}"))

        if border is None:
            border = OxmlElement(f"w:{border_name}")
            borders.append(border)

        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), color)


def set_table_vertical_borders(table, color):
    table_pr = table._tbl.tblPr
    borders = table_pr.find(qn("w:tblBorders"))

    if borders is None:
        borders = OxmlElement("w:tblBorders")
        table_pr.append(borders)

    for border_name in ("left", "right", "insideV"):
        border = borders.find(qn(f"w:{border_name}"))

        if border is None:
            border = OxmlElement(f"w:{border_name}")
            borders.append(border)

        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), color)


def apply_vertical_borders(table, color):
    set_table_vertical_borders(table, color)

    for row in table.rows:
        for cell in row.cells:
            set_cell_vertical_borders(cell, color)


def set_minimum_row_height(row, height):
    row.height = height
    row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST


def set_exact_row_height(row, height):
    row.height = height
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
