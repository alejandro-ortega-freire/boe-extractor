import re
from source.cleaning import clean_line, is_boe_noise


def normalize_module_section(section):
    section = clean_line(section)

    cut_patterns = [
        r"\bI\.?\s+PERFIL PROFESIONAL\b",
        r"\bII\.?\s+PERFIL PROFESIONAL\b",
        r"\bPERFIL PROFESIONAL DEL CERTIFICADO\b",
        r"\bUnidad de competencia\b",
        r"\bVinculación con capacitaciones profesionales\b",
    ]

    for pattern in cut_patterns:
        section = re.split(pattern, section, flags=re.IGNORECASE)[0]

    section = re.sub(r"\s+\bI\.\s*$", "", section).strip()

    section = re.sub(r"\s+(MF\d{4}_\d:)", r"\n\1", section)
    section = re.sub(r"\s+(MP\d{4}:)", r"\n\1", section)
    section = re.sub(r"\s+(UF\d{4})(?=[:\s\(])", r"\n\1", section)

    return section


def extract_modules(text):
    lines = text.splitlines()

    start = None
    for i, line in enumerate(lines):
        if "Relación de módulos formativos" in line:
            start = i + 1
            break

    if start is None:
        return []

    end = None
    for i in range(start, len(lines)):
        if lines[i].strip() in ("I.", "I"):
            end = i
            break

        if any(k in lines[i] for k in [
            "I. PERFIL PROFESIONAL",
            "II. PERFIL PROFESIONAL",
            "PERFIL PROFESIONAL DEL CERTIFICADO",
            "Unidad de competencia",
            "Vinculación con capacitaciones profesionales"
        ]):
            end = i
            break

    if end is None:
        end = len(lines)

    section = normalize_module_section("\n".join(lines[start:end]))

    raw_lines = [
        clean_line(line)
        for line in section.splitlines()
        if clean_line(line) and not is_boe_noise(line)
    ]

    modules = []
    current_module = None

    for line in raw_lines:
        if re.match(r"^MF\d{4}_\d:", line) or re.match(r"^MP\d{4}:", line):
            current_module = {"text": line, "ufs": []}
            modules.append(current_module)

        elif re.match(r"^UF\d{4}", line) and current_module:
            current_module["ufs"].append(line)

        else:
            if current_module:
                if current_module["ufs"]:
                    current_module["ufs"][-1] += " " + line
                else:
                    current_module["text"] += " " + line

    return modules


def calculate_certificate_duration(modules):
    mf_hours = 0
    mp_hours = 0

    for module in modules:
        module_text = module.get("text", "")
        hours_found = re.findall(r"\((\d+)\s*horas?\)", module_text, flags=re.IGNORECASE)

        if not hours_found:
            continue

        hours = int(hours_found[-1])

        if module_text.startswith("MF"):
            mf_hours += hours
        elif module_text.startswith("MP"):
            mp_hours += hours

    if mp_hours > 0:
        return f"{mf_hours}h + {mp_hours}h FEM"

    return f"{mf_hours}h"
