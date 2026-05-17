def get_value_after_label(lines, label):
    for i, line in enumerate(lines):
        if line.startswith(label):
            value = line.replace(label, "").strip()

            if value:
                return value

            for next_line in lines[i + 1:i + 4]:
                if next_line and ":" not in next_line:
                    return next_line.strip()

    return ""


def extract_basic_data(text):
    lines = text.splitlines()

    familia = get_value_after_label(lines, "Familia profesional:")
    familia = familia.split("Área profesional:")[0].strip()

    return {
        "nombre": get_value_after_label(lines, "Denominación:"),
        "codigo": get_value_after_label(lines, "Código:"),
        "familia": familia,
        "nivel": get_value_after_label(lines, "Nivel de cualificación profesional:"),
    }