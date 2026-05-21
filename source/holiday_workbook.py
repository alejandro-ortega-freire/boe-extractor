from datetime import date, datetime, timedelta
import posixpath
import re
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


CUSTOM_HOLIDAY_PLACEHOLDER = "Festividad añadida por el usuario"
EXCEL_EPOCH = date(1899, 12, 30)
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def parse_holiday_date(value):
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, (int, float)):
        return EXCEL_EPOCH + timedelta(days=int(value))

    text = str(value or "").strip()

    if not text:
        return None

    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue

    return None


def column_index(cell_reference):
    letters = re.match(r"([A-Z]+)", cell_reference or "")

    if not letters:
        return 0

    index = 0
    for letter in letters.group(1):
        index = index * 26 + (ord(letter) - ord("A") + 1)

    return index - 1


def read_shared_strings(archive):
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []

    strings = []
    namespace = {"m": MAIN_NS}

    for item in root.findall("m:si", namespace):
        text_parts = [node.text or "" for node in item.findall(".//m:t", namespace)]
        strings.append("".join(text_parts))

    return strings


def first_sheet_path(archive):
    try:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    except KeyError:
        return "xl/worksheets/sheet1.xml"

    namespace = {
        "m": MAIN_NS,
        "r": OFFICE_REL_NS,
        "rel": REL_NS,
    }
    sheet = workbook.find("m:sheets/m:sheet", namespace)

    if sheet is None:
        return "xl/worksheets/sheet1.xml"

    relationship_id = sheet.attrib.get(f"{{{OFFICE_REL_NS}}}id")

    for relationship in rels.findall("rel:Relationship", namespace):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib.get("Target", "worksheets/sheet1.xml")
            return posixpath.normpath(posixpath.join("xl", target))

    return "xl/worksheets/sheet1.xml"


def cell_value(cell, shared_strings):
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        texts = [
            text_node.text or ""
            for text_node in cell.findall(f".//{{{MAIN_NS}}}t")
        ]
        return "".join(texts)

    value_node = cell.find(f"{{{MAIN_NS}}}v")

    if value_node is None or value_node.text is None:
        return ""

    value = value_node.text

    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return ""

    if re.match(r"^-?\d+(?:\.\d+)?$", value):
        number = float(value)
        return int(number) if number.is_integer() else number

    return value


def read_rows(path):
    with ZipFile(path) as archive:
        shared_strings = read_shared_strings(archive)
        sheet = ET.fromstring(archive.read(first_sheet_path(archive)))

    rows = []

    for row in sheet.findall(f".//{{{MAIN_NS}}}row"):
        values = []

        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            index = column_index(cell.attrib.get("r", ""))

            while len(values) <= index:
                values.append("")

            values[index] = cell_value(cell, shared_strings)

        rows.append(values)

    return rows


def load_custom_holidays(path="festivos.xlsx"):
    try:
        rows = read_rows(path)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        print(f"No se pudo leer {path}. Se ignorarán los festivos personalizados. Detalle: {exc}")
        return {}

    date_column = None
    name_column = None
    data_start = 0

    for row_index, row in enumerate(rows):
        normalized = [str(value or "").strip().lower() for value in row]

        if "fecha" in normalized:
            date_column = normalized.index("fecha")
            name_column = normalized.index("nombre") if "nombre" in normalized else None
            data_start = row_index + 1
            break

    if date_column is None:
        print(f"No se encontró la columna Fecha en {path}. Se ignorarán los festivos personalizados.")
        return {}

    holidays = {}

    for row_number, row in enumerate(rows[data_start:], start=data_start + 1):
        if date_column >= len(row):
            continue

        holiday_date = parse_holiday_date(row[date_column])

        if holiday_date is None:
            if any(str(value or "").strip() for value in row):
                print(f"Fecha no válida en {path}, fila {row_number}. Se ignora.")
            continue

        name = ""

        if name_column is not None and name_column < len(row):
            name = str(row[name_column] or "").strip()

        holidays[holiday_date] = name or CUSTOM_HOLIDAY_PLACEHOLDER

    return holidays


def inline_string_cell(reference, text):
    escaped = (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f'<c r="{reference}" t="inlineStr"><is><t>{escaped}</t></is></c>'


def write_holiday_template(path="festivos.xlsx", data_rows=None):
    rows = [
        (1, [
            inline_string_cell(
                "A1",
                "Añade aquí festivos personalizados. La columna Fecha es obligatoria y debe usar dd/mm/aaaa. El nombre es opcional.",
            )
        ]),
        (2, [inline_string_cell("A2", "Ejemplo: 24/06/2026 en Fecha y San Juan en Nombre.")]),
        (4, [inline_string_cell("A4", "Fecha"), inline_string_cell("B4", "Nombre")]),
    ]

    for offset, (holiday_date, name) in enumerate(data_rows or [], start=5):
        rows.append((
            offset,
            [
                inline_string_cell(f"A{offset}", holiday_date),
                inline_string_cell(f"B{offset}", name),
            ],
        ))

    sheet_rows = "\n".join(
        f'<row r="{row_number}">' + "".join(cells) + "</row>"
        for row_number, cells in rows
    )
    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{MAIN_NS}" xmlns:r="{OFFICE_REL_NS}">
  <cols><col min="1" max="1" width="18" customWidth="1"/><col min="2" max="2" width="38" customWidth="1"/></cols>
  <sheetData>{sheet_rows}</sheetData>
</worksheet>'''

    workbook_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{MAIN_NS}" xmlns:r="{OFFICE_REL_NS}">
  <sheets><sheet name="Festivos" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''

    workbook_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="{OFFICE_REL_NS}/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>'''

    root_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="{OFFICE_REL_NS}/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>'''

    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
