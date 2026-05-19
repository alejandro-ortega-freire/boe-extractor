import re
import unicodedata

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

from source.anexo_iii_writer import (
    ACTION_CODE,
    PLACEHOLDER_ADDRESS,
    PLACEHOLDER_CENTER,
    PLACEHOLDER_LOCALITY,
    PROVINCE,
    duration_for_anexo,
    schedule_date_range,
    set_table_width_percent,
)
from source.schedule import code_from_text, format_date_range


ANEXO_IV_FONT_SIZE = 10
TABLE_HEADER_FILL = "D9D9D9"
WHITE_FILL = "FFFFFF"
LIGHT_BORDER = "BFBFBF"
UF_ROW_MIN_HEIGHT = Cm(1.4)
MAIN_HEADER_ROW_HEIGHT = Cm(2.6)
SUGGESTION_COLOR = RGBColor(192, 0, 0)
SMALL_CONTENT_SPLIT_PENALTY = 4.0
MAX_CONTENT_PARTS = 2
ASSIGNMENT_WINDOW = 1
STOPWORDS = {
    "a", "al", "ante", "asi", "cada", "como", "con", "contra", "de", "del",
    "desde", "el", "en", "entre", "e", "la", "las", "lo", "los", "o", "para",
    "por", "que", "se", "segun", "sin", "sobre", "su", "sus", "un", "una",
    "unas", "unos", "y",
    "accion", "acciones", "actividad", "actividades", "adecuado", "adecuados",
    "aplicar", "aplicacion", "aplicaciones", "caracteristicas", "caso",
    "criterio", "criterios", "datos", "definir", "describir", "determinar",
    "diferentes", "documento", "documentos", "efectuar", "elaborar",
    "establecer", "forma", "funcion", "funciones", "identificar", "indicar",
    "informacion", "mediante", "necesario", "obtener", "procedimiento",
    "procedimientos", "proceso", "procesos", "realizar", "relacion",
    "utilizar",
}
DOMAIN_SYNONYMS = {
    "email": ["correo", "electronico", "mensaje"],
    "correo": ["email", "electronico", "mensaje", "correspondencia"],
    "correspondencia": ["correo", "mensaje"],
    "mensaje": ["correo", "correspondencia"],
    "ofimatica": ["procesador", "textos", "hoja", "calculo", "presentacion"],
    "procesador": ["texto", "textos", "documento"],
    "textos": ["procesador", "documento", "redaccion"],
    "plantilla": ["modelo", "documento"],
    "plantillas": ["modelo", "documento"],
    "base": ["datos"],
    "datos": ["base", "registro"],
    "hoja": ["calculo"],
    "calculo": ["hoja"],
    "presentacion": ["diapositiva", "grafica"],
    "presentaciones": ["diapositiva", "grafica"],
    "archivo": ["fichero", "carpeta"],
    "archivos": ["ficheros", "carpetas"],
    "carpeta": ["archivo", "fichero"],
    "carpetas": ["archivos", "ficheros"],
    "seguridad": ["confidencialidad", "integridad", "proteccion"],
    "urgencia": ["emergencia"],
    "urgencias": ["emergencias"],
    "emergencia": ["urgencia"],
    "emergencias": ["urgencias"],
}
TECHNICAL_EXPRESSIONS = {
    "base datos",
    "bases datos",
    "correo electronico",
    "hoja calculo",
    "hojas calculo",
    "procesador textos",
    "sistema operativo",
    "soporte vital",
    "soporte vital basico",
    "soporte vital avanzado",
    "aplicaciones informaticas",
    "bases datos relacionales",
    "correo electronico",
    "firma electronica",
    "tratamiento textos",
    "presentaciones graficas",
}
NEGATIVE_KEYWORD_GROUPS = [
    {"correo", "electronico", "mensaje", "correspondencia"},
    {"texto", "textos", "procesador", "redaccion", "plantilla", "plantillas"},
    {"calculo", "hoja", "hojas"},
    {"base", "bases", "datos", "registro", "registros"},
    {"presentacion", "presentaciones", "diapositiva", "grafica", "graficas"},
    {"archivo", "archivos", "fichero", "ficheros", "carpeta", "carpetas"},
    {"seguridad", "confidencialidad", "integridad", "proteccion"},
    {"urgencia", "urgencias", "emergencia", "emergencias"},
]


def configure_page(section):
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def set_cell_vertical_borders(cell, color=LIGHT_BORDER):
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


def set_table_vertical_borders(table, color=LIGHT_BORDER):
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


def apply_light_vertical_borders(table):
    set_table_vertical_borders(table)

    for row in table.rows:
        for cell in row.cells:
            set_cell_vertical_borders(cell)


def set_minimum_row_height(row, height=UF_ROW_MIN_HEIGHT):
    row.height = height
    row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST


def set_exact_row_height(row, height):
    row.height = height
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY


def set_cell_text(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(str(text or ""))
    run.bold = bold
    run.font.size = Pt(ANEXO_IV_FONT_SIZE)


def clear_cell(cell):
    cell.text = ""
    cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    return paragraph


def add_prefixed_text(paragraph, text, italic=False):
    text = str(text or "").strip()

    if not text:
        return

    parts = text.split(" ", 1)
    prefix = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    prefix_run = paragraph.add_run(prefix)
    prefix_run.bold = True
    prefix_run.italic = italic
    prefix_run.font.size = Pt(ANEXO_IV_FONT_SIZE)

    if rest:
        text_run = paragraph.add_run(" " + rest)
        text_run.italic = italic
        text_run.font.size = Pt(ANEXO_IV_FONT_SIZE)


def set_criterion_cell_text(cell, criterion, include_subcriteria=False):
    paragraph = clear_cell(cell)
    add_prefixed_text(paragraph, criterion.get("text", ""))

    if not include_subcriteria:
        return

    if criterion.get("subcriteria"):
        spacer = cell.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(0)

    for subcriterion in criterion.get("subcriteria", []):
        paragraph = cell.add_paragraph()
        paragraph.paragraph_format.left_indent = Pt(0)
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        add_prefixed_text(paragraph, subcriterion.get("text", ""), italic=True)

        for bullet in subcriterion.get("bullets", []):
            add_hyphen_item(cell, bullet, italic=True)


def add_bold_cell_paragraph(cell, text, space_before=0):
    paragraph = cell.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text)
    run.bold = True
    run.font.size = Pt(ANEXO_IV_FONT_SIZE)
    return paragraph


def add_cell_text_paragraph(cell, text):
    paragraph = cell.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(str(text or ""))
    run.font.size = Pt(ANEXO_IV_FONT_SIZE)
    return paragraph


def add_hyphen_item(cell, text, level=0, italic=False, color=None):
    paragraph = cell.add_paragraph()
    indent = 7 + (level * 8)
    paragraph.paragraph_format.left_indent = Pt(indent)
    paragraph.paragraph_format.first_line_indent = Pt(-7)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(f"- {text}")
    run.font.size = Pt(ANEXO_IV_FONT_SIZE)
    run.italic = italic
    if color:
        run.font.color.rgb = color
    return paragraph


def set_spaces_equipment_cell_text(cell, spaces=None, equipment_groups=None):
    spaces = [space for space in (spaces or []) if space]
    equipment_items = []

    for group in equipment_groups or []:
        equipment_items.extend(item for item in group.get("items", []) if item)

    clear_cell(cell)
    cell.paragraphs[0].paragraph_format.space_after = Pt(0)
    cell.paragraphs[0].add_run("Espacio formativo").bold = True
    cell.paragraphs[0].runs[0].font.size = Pt(ANEXO_IV_FONT_SIZE)

    if len(spaces) == 1:
        add_cell_text_paragraph(cell, spaces[0])
    else:
        for space in spaces:
            add_hyphen_item(cell, space)

    add_bold_cell_paragraph(cell, "Equipamiento", space_before=8)

    for item in equipment_items:
        add_hyphen_item(cell, item)


def add_content_bullets(cell, bullets, level=0, color=None):
    for bullet in bullets or []:
        text = bullet.get("text", "")

        if text:
            add_hyphen_item(cell, text, level, color=color)

        add_content_bullets(cell, bullet.get("children", []), level + 1, color=color)


def set_contents_cell_text(cell, contents=None, suggested=False):
    contents = contents or []
    clear_cell(cell)
    color = SUGGESTION_COLOR if suggested else None

    if not contents:
        return

    for index, content in enumerate(contents):
        title = content.get("title", "")

        if title:
            paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
            paragraph.paragraph_format.space_before = Pt(6 if index else 0)
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(title)
            run.bold = True
            run.font.size = Pt(ANEXO_IV_FONT_SIZE)
            if color:
                run.font.color.rgb = color

        add_content_bullets(cell, content.get("bullets", []), color=color)


def strip_accents(text):
    normalized = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def keyword_tokens(text):
    words = re.findall(r"[a-záéíóúüñ0-9]+", strip_accents(text))
    tokens = [
        word
        for word in words
        if len(word) > 2 and word not in STOPWORDS
    ]
    expanded = list(tokens)

    for token in tokens:
        expanded.extend(DOMAIN_SYNONYMS.get(token, []))

    return expanded


def weighted_keywords(text):
    tokens = keyword_tokens(text)
    weights = {}

    for token in tokens:
        weights[token] = weights.get(token, 0) + 1.0

    normalized_text = " ".join(tokens)

    for expression in TECHNICAL_EXPRESSIONS:
        if expression in normalized_text:
            weights[expression] = weights.get(expression, 0) + 5.0

    for size, weight in ((2, 2.4), (3, 3.2)):
        for index in range(0, max(len(tokens) - size + 1, 0)):
            phrase = " ".join(tokens[index:index + size])
            weights[phrase] = weights.get(phrase, 0) + weight

    return weights


def criterion_keywords(criterion):
    parts = [criterion.get("text", "")]

    for subcriterion in criterion.get("subcriteria", []):
        parts.append(subcriterion.get("text", ""))
        parts.extend(subcriterion.get("bullets", []))

    return weighted_keywords(" ".join(parts))


def bullet_plain_text(bullet):
    parts = [bullet.get("text", "")]

    for child in bullet.get("children", []):
        parts.append(bullet_plain_text(child))

    return " ".join(part for part in parts if part)


def content_segment_text(content, bullet=None):
    parts = [content.get("title", "")]

    if bullet:
        parts.append(bullet_plain_text(bullet))
    else:
        parts.extend(bullet_plain_text(item) for item in content.get("bullets", []))

    return " ".join(part for part in parts if part)


def content_similarity(criteria_weights, text):
    content_weights = weighted_keywords(text)

    if not criteria_weights or not content_weights:
        return 0.0

    positive_score = sum(
        min(weight, criteria_weights.get(token, 0))
        for token, weight in content_weights.items()
    )
    criteria_tokens = set(criteria_weights)
    content_tokens = set(content_weights)
    negative_penalty = 0.0

    for group in NEGATIVE_KEYWORD_GROUPS:
        if criteria_tokens & group:
            continue

        if content_tokens & group:
            negative_penalty += 1.5

    return positive_score - negative_penalty


def clone_content_with_bullets(content, bullets, suffix=""):
    title = content.get("title", "")

    if suffix and title:
        title = f"{title} ({suffix})"

    return {
        "title": title,
        "bullets": bullets,
    }


def split_bullets_into_chunks(bullets, max_parts, allow_extra_parts=False):
    total = len(bullets)

    if total <= 1:
        return [bullets]

    part_limit = total if allow_extra_parts else MAX_CONTENT_PARTS
    parts = min(max_parts, part_limit, total)

    if parts < 2:
        return [bullets]

    base_size = total // parts
    remainder = total % parts
    chunks = []
    start = 0

    for index in range(parts):
        size = base_size + (1 if index < remainder else 0)
        end = start + size
        chunks.append(bullets[start:end])
        start = end

    return chunks


def split_content_segments(contents, criterion_count=1):
    segments = []

    for content_index, content in enumerate(contents or []):
        bullets = content.get("bullets", [])

        if bullets:
            chunks = split_bullets_into_chunks(bullets, criterion_count)
            bullet_start = 0

            for chunk in chunks:
                segments.append({
                    "content_index": content_index,
                    "bullet_index": bullet_start,
                    "content": content,
                    "bullets": chunk,
                    "is_split": len(chunks) > 1,
                    "text": " ".join(
                        content_segment_text(content, bullet)
                        for bullet in chunk
                    ),
                })
                bullet_start += len(chunk)
        else:
            segments.append({
                "content_index": content_index,
                "bullet_index": 0,
                "content": content,
                "bullets": [],
                "is_split": False,
                "text": content_segment_text(content),
            })

    if len(segments) < criterion_count:
        fallback_segments = split_content_segments_for_coverage(contents)

        if len(fallback_segments) > len(segments):
            return fallback_segments

    return segments


def split_content_segments_for_coverage(contents):
    segments = []

    for content_index, content in enumerate(contents or []):
        bullets = content.get("bullets", [])

        if bullets:
            chunks = split_bullets_into_chunks(
                bullets,
                max(len(bullets), 1),
                allow_extra_parts=True
            )
            bullet_start = 0

            for chunk in chunks:
                segments.append({
                    "content_index": content_index,
                    "bullet_index": bullet_start,
                    "content": content,
                    "bullets": chunk,
                    "is_split": len(chunks) > 1,
                    "text": " ".join(
                        content_segment_text(content, bullet)
                        for bullet in chunk
                    ),
                })
                bullet_start += len(chunk)
        else:
            segments.append({
                "content_index": content_index,
                "bullet_index": 0,
                "content": content,
                "bullets": [],
                "is_split": False,
                "text": content_segment_text(content),
            })

    return segments


def roman_suffix(index):
    suffixes = ["I", "II", "III", "IV", "V", "VI"]
    return suffixes[index] if index < len(suffixes) else str(index + 1)


def rebalance_empty_content_assignments(assigned_segments):
    if not assigned_segments:
        return assigned_segments

    empty_indexes = [
        index
        for index, segments in enumerate(assigned_segments)
        if not segments
    ]

    for empty_index in empty_indexes:
        donors = [
            index
            for index, segments in enumerate(assigned_segments)
            if len(segments) > 1
        ]

        if not donors:
            break

        donor_index = min(
            donors,
            key=lambda index: (abs(index - empty_index), index > empty_index)
        )

        if donor_index < empty_index:
            segment = assigned_segments[donor_index].pop()
        else:
            segment = assigned_segments[donor_index].pop(0)

        assigned_segments[empty_index].append(segment)

    return assigned_segments


def ensure_all_segments_assigned(assigned_segments, segments):
    assigned_ids = {
        id(segment)
        for criterion_segments in assigned_segments
        for segment in criterion_segments
    }
    missing_segments = [
        segment
        for segment in segments
        if id(segment) not in assigned_ids
    ]

    if not missing_segments:
        return assigned_segments

    for segment in missing_segments:
        expected = round(
            len(assigned_segments)
            * segment["content_index"]
            / max(len({item["content_index"] for item in segments}), 1)
        )
        target_index = min(expected, len(assigned_segments) - 1)
        assigned_segments[target_index].append(segment)

    return assigned_segments


def assign_contents_to_criteria(criteria, contents):
    if not criteria:
        return []

    if len(criteria) == 1:
        return [contents or []]

    segments = split_content_segments(contents, len(criteria))
    assigned_segments = [[] for _ in criteria]

    if not segments:
        return assigned_segments

    criteria_weights = [criterion_keywords(criterion) for criterion in criteria]
    min_criterion_index = 0

    for segment_index, segment in enumerate(segments):
        expected = round(
            segment_index * (len(criteria) - 1) / max(len(segments) - 1, 1)
        )
        best_index = min_criterion_index
        best_score = None

        lower_bound = max(min_criterion_index, expected - ASSIGNMENT_WINDOW)
        upper_bound = min(len(criteria) - 1, expected + ASSIGNMENT_WINDOW)

        if lower_bound > upper_bound:
            lower_bound = min_criterion_index
            upper_bound = min(len(criteria) - 1, min_criterion_index + ASSIGNMENT_WINDOW)

        for criterion_index in range(lower_bound, upper_bound + 1):
            similarity = content_similarity(criteria_weights[criterion_index], segment["text"])
            order_penalty = abs(criterion_index - expected) * 1.25
            split_penalty = SMALL_CONTENT_SPLIT_PENALTY if segment.get("is_split") else 0
            score = similarity - order_penalty - split_penalty

            if best_score is None or score > best_score:
                best_score = score
                best_index = criterion_index

        assigned_segments[best_index].append(segment)
        min_criterion_index = best_index

    assigned_segments = ensure_all_segments_assigned(assigned_segments, segments)
    assigned_segments = rebalance_empty_content_assignments(assigned_segments)
    assigned_segments = ensure_all_segments_assigned(assigned_segments, segments)

    part_positions = {}
    for content_index in sorted({segment["content_index"] for segment in segments}):
        positions = [
            criterion_index
            for criterion_index, criterion_segments in enumerate(assigned_segments)
            if any(segment["content_index"] == content_index for segment in criterion_segments)
        ]
        if len(positions) > 1:
            part_positions[content_index] = positions

    return [
        build_contents_from_segments(
            contents,
            segments_for_criterion,
            part_positions,
            criterion_index
        )
        for criterion_index, segments_for_criterion in enumerate(assigned_segments)
    ]


def build_contents_from_segments(contents, segments, part_positions=None, criterion_index=0):
    if not segments:
        return []

    part_positions = part_positions or {}
    content_indices_in_parts = {}

    for segment in segments:
        content_indices_in_parts.setdefault(segment["content_index"], []).append(segment)

    result = []

    for content_index in sorted(content_indices_in_parts):
        grouped = sorted(
            content_indices_in_parts[content_index],
            key=lambda item: item["bullet_index"]
        )
        content = grouped[0]["content"]
        suffix = ""

        if content_index in part_positions:
            suffix = roman_suffix(part_positions[content_index].index(criterion_index))

        bullets = []
        for segment in grouped:
            bullets.extend(segment["bullets"])

        result.append(clone_content_with_bullets(content, bullets, suffix))

    return result


def set_strategy_placeholder_cell_text(cell):
    titles = [
        "SESIÓN 1",
        "ESTRATEGIA\nMETODOLÓGICA",
        "Inicio (1h)",
        "Desarrollo (4h)",
        "Final (1h)",
        "ACTIVIDAD DE\nAPRENDIZAJE",
        "RECURSOS\nDIDÁCTICOS",
    ]

    clear_cell(cell)

    for index, title in enumerate(titles):
        if index == 0:
            paragraph = cell.paragraphs[0]
        else:
            paragraph = cell.add_paragraph()

        paragraph.paragraph_format.space_before = Pt(8 if index else 0)
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(title)
        run.bold = True
        run.font.size = Pt(ANEXO_IV_FONT_SIZE)

        text_paragraph = cell.add_paragraph()
        text_paragraph.paragraph_format.space_before = Pt(0)
        text_paragraph.paragraph_format.space_after = Pt(0)
        text_run = text_paragraph.add_run("Lorem ipsum dolor met")
        text_run.font.size = Pt(ANEXO_IV_FONT_SIZE)


def add_horizontal_line(doc):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(14)
    paragraph.paragraph_format.space_after = Pt(10)

    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "000000")
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def add_heading(doc, text, size=12, space_after=6):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(space_after)
    run = paragraph.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    return paragraph


def add_label_value(paragraph, label, value):
    label_run = paragraph.add_run(label)
    label_run.bold = True
    label_run.font.size = Pt(ANEXO_IV_FONT_SIZE)
    value_run = paragraph.add_run(str(value or ""))
    value_run.font.size = Pt(ANEXO_IV_FONT_SIZE)


def add_tabbed_line(doc, parts, tab_stops=None):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(0)

    tab_stops = tab_stops or [Inches(3.6)]
    for stop in tab_stops:
        paragraph.paragraph_format.tab_stops.add_tab_stop(stop)

    for index, (label, value) in enumerate(parts):
        if index:
            paragraph.add_run("\t")

        add_label_value(paragraph, label, value)

    return paragraph


def scheduled_text(schedule, code):
    if not schedule:
        return ""

    return schedule.get("dates_by_code", {}).get(code, {}).get("text", "")


def module_title(module):
    identifier = module.get("identifier", "")
    return identifier.replace(":", "", 1).strip()


def module_schedule_text(schedule, module):
    module_code = code_from_text(module.get("identifier", ""))
    direct_dates = scheduled_text(schedule, module_code)

    if direct_dates:
        return direct_dates

    uf_dates = []

    for uf in module.get("ufs", []):
        scheduled = schedule.get("dates_by_code", {}).get(uf.get("code", "")) if schedule else None

        if scheduled:
            uf_dates.append(scheduled)

    if not uf_dates:
        return ""

    first = uf_dates[0]
    last = uf_dates[-1]
    return format_date_range(first["start"], last["end"])


def build_module_filename(module_code, certificate_code):
    return f"anexoIV_{module_code}_{certificate_code}.docx"


def add_module_header(doc, data, module, duration_text, schedule):
    add_heading(doc, f"ANEXO IV - {module_title(module)}", size=12, space_after=8)
    add_heading(doc, "Programación didáctica", size=12, space_after=4)
    add_heading(doc, "(Modalidad Presencial)", size=12, space_after=16)

    certificate = f"{data.get('codigo', '')} {data.get('nombre', '').upper()}".strip()

    add_tabbed_line(doc, [("CERTIFICADO PROFESIONAL: ", certificate)])
    add_tabbed_line(doc, [("FAMILIA PROFESIONAL: ", data.get("familia", ""))])
    add_tabbed_line(doc, [("NIVEL DE CUALIFICACIÓN PROFESIONAL: ", data.get("nivel", ""))])
    doc.add_paragraph("")

    add_tabbed_line(
        doc,
        [
            ("DURACIÓN DEL CERTIFICADO: ", duration_for_anexo(duration_text)),
            ("FECHAS DE IMPARTICIÓN: ", schedule_date_range(schedule)),
        ],
        tab_stops=[Inches(3.8)],
    )
    add_tabbed_line(doc, [("CENTRO DE FORMACIÓN: ", PLACEHOLDER_CENTER)])
    add_tabbed_line(doc, [("DIRECCIÓN: ", PLACEHOLDER_ADDRESS)])
    add_tabbed_line(
        doc,
        [
            ("LOCALIDAD: ", PLACEHOLDER_LOCALITY),
            ("PROVINCIA: ", PROVINCE),
        ],
        tab_stops=[Inches(3.8)],
    )
    doc.add_paragraph("")

    add_heading(doc, "PROGRAMACIÓN DIDÁCTICA DEL MÓDULO PROFESIONAL", size=11, space_after=8)

    module_dates = module_schedule_text(schedule, module)

    add_tabbed_line(doc, [("IDENTIFICACIÓN DEL MÓDULO PROFESIONAL: ", module.get("identifier", ""))])
    add_tabbed_line(
        doc,
        [
            ("HORAS: ", module.get("hours", "")),
            ("FECHAS DE IMPARTICIÓN DEL MÓDULO: ", module_dates),
        ],
        tab_stops=[Inches(1.2)],
    )
    add_tabbed_line(doc, [("Nº DE CURSO: ", ACTION_CODE)])
    add_tabbed_line(doc, [("Objetivo general del módulo: ", module.get("objective", ""))])


def add_anexo_iv_table(
    doc,
    module,
    schedule,
    copy_subcriteria=False,
    spaces=None,
    equipment_groups=None
):
    add_horizontal_line(doc)

    table = doc.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = False
    set_table_width_percent(table, 100)

    headers = [
        "Objetivos específicos\nLogro de los\nresultados de\naprendizaje ¹",
        "Contenidos²",
        "Estrategias\nmetodológicas,\nactividades de\naprendizaje y\nrecursos didácticos³",
        "Espacios,\ninstalaciones y\nequipamiento⁴",
    ]
    widths = [Cm(4.0), Cm(4.0), Cm(4.0), Cm(4.0)]

    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        set_cell_shading(cell, TABLE_HEADER_FILL)
        set_cell_text(cell, header)
        cell.width = widths[index]

    set_exact_row_height(table.rows[0], MAIN_HEADER_ROW_HEIGHT)

    ufs = module.get("ufs", [])

    if not ufs:
        criteria = module.get("criteria", []) or [{}]
        contents_by_criterion = assign_contents_to_criteria(criteria, module.get("contents", []))
        suggested_contents = len(criteria) > 1

        for criterion_index, criterion in enumerate(criteria):
            cells = table.add_row().cells

            for index, cell in enumerate(cells):
                cell.width = widths[index]

            set_criterion_cell_text(cells[0], criterion, copy_subcriteria)

            for cell in cells[1:2]:
                set_cell_text(cell, "")

            set_contents_cell_text(
                cells[1],
                contents_by_criterion[criterion_index],
                suggested=suggested_contents
            )
            set_strategy_placeholder_cell_text(cells[2])
            set_spaces_equipment_cell_text(cells[3], spaces, equipment_groups)

        apply_light_vertical_borders(table)
        return table

    for uf in ufs:
        uf_code = uf.get("code", "")
        uf_name = uf.get("name", "")
        uf_dates = scheduled_text(schedule, uf_code)

        top_cells = table.add_row().cells
        bottom_cells = table.add_row().cells
        set_minimum_row_height(table.rows[-2])
        set_minimum_row_height(table.rows[-1])

        for row_cells in (top_cells, bottom_cells):
            for index, cell in enumerate(row_cells):
                set_cell_shading(cell, TABLE_HEADER_FILL)
                cell.width = widths[index]

        uf_label_cell = top_cells[0].merge(bottom_cells[0])
        uf_name_cell = top_cells[1].merge(bottom_cells[1])

        set_cell_text(uf_label_cell, "Unidad Formativa\n(UF)")
        set_cell_text(uf_name_cell, f"{uf_code}: {uf_name}".strip(": "))
        set_cell_shading(uf_name_cell, WHITE_FILL)

        set_cell_text(top_cells[2], "Horas")
        set_cell_text(top_cells[3], uf.get("hours", ""), align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_shading(top_cells[3], WHITE_FILL)

        set_cell_text(bottom_cells[2], "Fechas de impartición")
        set_cell_text(bottom_cells[3], uf_dates, align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_shading(bottom_cells[3], WHITE_FILL)

        criteria = uf.get("criteria", []) or [{}]
        contents_by_criterion = assign_contents_to_criteria(criteria, uf.get("contents", []))
        suggested_contents = len(criteria) > 1

        for criterion_index, criterion in enumerate(criteria):
            cells = table.add_row().cells
            for index, cell in enumerate(cells):
                cell.width = widths[index]

            set_criterion_cell_text(cells[0], criterion, copy_subcriteria)
            for cell in cells[1:2]:
                set_cell_text(cell, "")

            set_contents_cell_text(
                cells[1],
                contents_by_criterion[criterion_index],
                suggested=suggested_contents
            )
            set_strategy_placeholder_cell_text(cells[2])
            set_spaces_equipment_cell_text(cells[3], spaces, equipment_groups)

    apply_light_vertical_borders(table)
    return table


def create_anexo_iv_docx(
    data,
    module,
    duration_text,
    output_path,
    schedule=None,
    add_header_footer=None,
    copy_subcriteria=False,
    spaces=None,
    equipment_groups=None,
    teacher_name="Docente"
):
    doc = Document()
    configure_page(doc.sections[0])

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(ANEXO_IV_FONT_SIZE)

    add_module_header(doc, data, module, duration_text, schedule)
    add_anexo_iv_table(doc, module, schedule, copy_subcriteria, spaces, equipment_groups)

    if add_header_footer is None:
        from source.word_writer import add_header_footer

    add_header_footer(doc, teacher_name)

    doc.save(output_path)
