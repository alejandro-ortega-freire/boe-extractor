import re

from source.cleaning import clean_line, dedupe_list, is_boe_noise, clean_dot_leaders
from source.geometry import merge_lowercase_continuations


def fallback_spaces_from_text(text):
    lines = merge_lowercase_continuations(text.splitlines())

    start = None
    for i, line in enumerate(lines):
        if "REQUISITOS MÍNIMOS DE ESPACIOS" in line:
            start = i
            break

    if start is None:
        return []

    section = lines[start:]
    spaces = []

    for i, line in enumerate(section):
        line = clean_line(line)

        if not line:
            continue

        if "Equipamiento" in line:
            break

        if "Superficie" in line or "Espacio Formativo" in line:
            continue

        if line.lower().startswith("alumnos"):
            continue

        if "m2" in line.lower():
            continue

        nearby = clean_line(" ".join(section[i:i + 4]))

        if re.search(r"\bX\b", nearby):
            continue

        nums = re.findall(r"\b\d+(?:,\d+)?\b", nearby)

        if len(nums) >= 2:
            name = re.sub(r"\b\d+(?:,\d+)?\b", "", line).strip()
            name = clean_line(name)
            name = clean_dot_leaders(name)
            name = re.sub(r"\s*\.\s*$", "", name)

            if name and len(name) > 3 and not name.lower().startswith("alumnos"):
                spaces.append(
                    f"{name} de {nums[0]} m2 (para 15 alumnos) o de {nums[1]} m2 (para 25 alumnos)"
                )

    return dedupe_list(spaces)


def fallback_equipment_from_text(text):
    lines = text.splitlines()

    start = None
    for i, line in enumerate(lines):
        if "Equipamiento" in line:
            start = i + 1
            break

    if start is None:
        return []

    items = []

    for line in lines[start:]:
        line = clean_line(line)

        if not line:
            continue

        if any(stop in line for stop in [
            "No debe interpretarse",
            "Las instalaciones",
            "II PERFIL PROFESIONAL",
            "Unidad de competencia",
            "MÓDULO FORMATIVO",
            "ANEXO"
        ]):
            break

        if is_boe_noise(line):
            continue

        if line.startswith(("Espacio", "Superficie")):
            continue

        if re.fullmatch(r"[\dXx\s]+", line):
            continue

        starts_new = (
            line.startswith("-") or
            (line and line[0].isupper())
        )

        line = re.sub(r"^-+\s*", "", line).strip()
        line = clean_line(line)

        if not line:
            continue

        if starts_new or not items:
            items.append(line)
        else:
            items[-1] += " " + line

    if not items:
        return []

    return [{
        "name": "Equipamiento general",
        "items": dedupe_list(items)
    }]
