import re


WEEKDAY_PATTERN = r"(?:lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)"
MONTH_PATTERN = r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)"


def strip_boe_inline_noise(text):
    text = str(text or "")
    old_boe_date = rf"{WEEKDAY_PATTERN}\s+\d{{1,2}}\s+{MONTH_PATTERN}\s+\d{{4}}"
    patterns = [
        rf"\b\d{{4,6}}\s+{old_boe_date}\s+BOE\s+n[úu]m\.?\s*\d+\b",
        rf"\bBOE\s+n[úu]m\.?\s*\d+\s+{old_boe_date}\s+\d{{4,6}}\b",
        rf"\b{old_boe_date}\b",
        r"\bBOE\s+n[úu]m\.?\s*\d+\b",
    ]

    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    return text


def is_boe_noise(line):
    patterns = [
        r"BOLETÍN OFICIAL DEL ESTADO",
        r"^BOE\s+n[úu]m\.?\s*\d+",
        r"^Núm\.?\s*\d+",
        r"^Sec\.?\s*[IVXLC]+\b",
        r"Pág\.?\s*\d+",
        r"cve:",
        r"BOE-A-\d{4}-\d+",
        r"\d{1,2}\s+de\s+[a-záéíóúñ]+\s+de\s+\d{4}",
        rf"^\d{{4,6}}\s+{WEEKDAY_PATTERN}\s+\d{{1,2}}\s+{MONTH_PATTERN}\s+\d{{4}}\s+BOE\s+n[úu]m\.?\s*\d+$",
        rf"^BOE\s+n[úu]m\.?\s*\d+\s+{WEEKDAY_PATTERN}\s+\d{{1,2}}\s+{MONTH_PATTERN}\s+\d{{4}}\s+\d{{4,6}}$",
    ]
    return any(re.search(p, str(line), re.IGNORECASE) for p in patterns)


def clean_line(line):
    if line is None:
        return ""

    line = str(line).strip()
    line = line.replace("●", "").replace("•", "")

    # Normaliza distintos tipos de guion que pueden venir del PDF.
    line = (
        line
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("‐", "-")
        .replace("-", "-")
        .replace("‒", "-")
    )

    line = re.sub(r"BOE-A-\d{4}-\d+", "", line)
    line = strip_boe_inline_noise(line)

    # Elimina puntos decorativos largos, pero conserva CE1.2, 1.1, decimales, etc.
    line = re.sub(r"\.{3,}", " ", line)

    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"\s+([.,;:])", r"\1", line)
    return line.strip()


def clean_dot_leaders(text):
    """
    Limpia puntos decorativos separados por espacios:
    'Aula de gestión . . . . . .' -> 'Aula de gestión'

    No rompe numeraciones como CE1.2 porque solo actúa sobre
    secuencias de puntos repetidos, estén juntos o separados.
    """
    if text is None:
        return ""

    text = str(text)
    text = re.sub(r"\s*\.\s*(?:\.\s*){2,}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text(text):
    cleaned = []

    for line in text.splitlines():
        if is_boe_noise(line):
            continue

        line = clean_line(line)

        if line:
            cleaned.append(line)

    return "\n".join(cleaned)


def dedupe_list(values):
    result = []
    seen = set()

    for value in values:
        value = clean_line(value)

        if value and value not in seen:
            result.append(value)
            seen.add(value)

    return result


def dedupe_groups(groups):
    result = []
    seen = set()

    for group in groups:
        name = clean_line(group.get("name", ""))
        items = dedupe_list(group.get("items", []))
        key = (name, tuple(items))

        if name and items and key not in seen:
            result.append({
                "name": name,
                "items": items
            })
            seen.add(key)

    return result
