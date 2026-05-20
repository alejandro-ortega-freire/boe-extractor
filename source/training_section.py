import re

from source.cleaning import clean_line


def normalize_title_case(text):
    text = clean_line(text)

    if text and text == text.upper():
        return text.lower().capitalize()

    return text


def strip_module_hours(module_text):
    return re.sub(
        r"\s*\(\d+\s*horas?\)\s*$",
        "",
        module_text,
        flags=re.IGNORECASE
    ).strip()


def extract_hours(text):
    found = re.findall(
        r"\((\d+)\s*horas?\)|Duración:\s*(\d+)\s*horas?",
        text,
        flags=re.IGNORECASE
    )

    if not found:
        return ""

    last = found[-1]
    return next((value for value in last if value), "")


def extract_uc_objective(text):
    text = clean_line(text)
    text = re.sub(r"\bUC\d{4}_\d\b\s*:?", "", text).strip()
    text = re.sub(r"^:\s*", "", text).strip()
    return clean_line(text)


def is_module_header(line):
    """Detect module starts with or without accent: BOEs may use MÓDULO or MODULO."""
    return bool(re.match(r"^M[ÓO]DULO FORMATIVO\s+\d+", line, flags=re.IGNORECASE))


def is_uf_header(line):
    return bool(re.match(r"^UNIDAD FORMATIVA\s+\d+", line, flags=re.IGNORECASE))


def is_practice_module_header(line):
    return bool(re.match(r"^M[ÓO]DULO DE PRÁCTICAS", line, flags=re.IGNORECASE))


def get_first_value_after_label(lines, label):
    for i, line in enumerate(lines):
        if line.startswith(label):
            value = line.replace(label, "", 1).strip()

            if value:
                return value

            parts = []

            for next_line in lines[i + 1:i + 6]:
                next_line = clean_line(next_line)

                if not next_line:
                    continue

                if re.match(
                    r"^(Código:|Nivel de cualificación profesional:|Asociado a la Unidad de Competencia:|Duración:|Capacidades y criterios de evaluación|UNIDAD FORMATIVA|M[ÓO]DULO FORMATIVO)",
                    next_line,
                    flags=re.IGNORECASE
                ):
                    break

                parts.append(next_line)

            return clean_line(" ".join(parts))

    return ""


def get_multiline_value_after_label(lines, label, stop_patterns):
    for i, line in enumerate(lines):
        if not line.startswith(label):
            continue

        parts = []

        value = line.replace(label, "", 1).strip()
        if value:
            parts.append(value)

        for next_line in lines[i + 1:]:
            next_line = clean_line(next_line)

            if not next_line:
                continue

            if any(re.match(pattern, next_line, flags=re.IGNORECASE) for pattern in stop_patterns):
                break

            parts.append(next_line)

        return clean_line(" ".join(parts))

    return ""


def extract_mf_code(lines):
    for line in lines:
        match = re.search(r"\bMF\d{4}_\d\b", line)
        if match:
            return match.group(0)

    return ""


def extract_uf_code(lines):
    for line in lines:
        match = re.search(r"\bUF\d{4}\b", line)
        if match:
            return match.group(0)

    return ""


def extract_duration(lines):
    for line in lines:
        if line.startswith("Duración:"):
            match = re.search(r"\d+", line)
            return match.group(0) if match else ""

    return ""


def split_criteria_line(line):
    line = clean_line(line)

    # Separa criterios y subcriterios aunque el PDF los haya pegado.
    line = re.sub(r"\s+(C\d+:)", r"\n\1", line)
    line = re.sub(r"\s+(CE\d+\.\d+)", r"\n\1", line)

    # Separa correctamente bullets internos.
    line = re.sub(r"\s+-\s*", r"\n- ", line)
    line = re.sub(r"(?m)^-\s*", "- ", line)

    return [
        clean_line(part)
        for part in line.splitlines()
        if clean_line(part)
    ]


def is_criteria_stop_line(line):
    return bool(
        line.startswith("Contenidos")
        or line.startswith("Orientaciones metodológicas")
        or line.startswith("Criterios de acceso")
        or is_module_header(line)
        or is_uf_header(line)
        or is_practice_module_header(line)
    )


def parse_criteria_block(block_lines):
    start = None

    for i, line in enumerate(block_lines):
        if line.startswith("Capacidades y criterios de evaluación"):
            start = i + 1
            break

    if start is None:
        return []

    expanded_lines = []

    for raw_line in block_lines[start:]:
        raw_line = clean_line(raw_line)

        if not raw_line:
            continue

        if is_criteria_stop_line(raw_line):
            break

        expanded_lines.extend(split_criteria_line(raw_line))

    criteria = []
    current_criterion = None
    current_subcriterion = None

    for line in expanded_lines:
        if re.match(r"^C\d+:", line):
            current_criterion = {
                "text": line,
                "subcriteria": []
            }
            criteria.append(current_criterion)
            current_subcriterion = None
            continue

        if re.match(r"^CE\d+\.\d+", line):
            if current_criterion is None:
                current_criterion = {
                    "text": "",
                    "subcriteria": []
                }
                criteria.append(current_criterion)

            current_subcriterion = {
                "text": line,
                "bullets": []
            }
            current_criterion["subcriteria"].append(current_subcriterion)
            continue

        if line.startswith("-"):
            bullet = re.sub(r"^-+\s*", "", line).strip()

            if current_subcriterion is not None and bullet:
                current_subcriterion["bullets"].append(bullet)

            continue

        if current_subcriterion is not None:
            if current_subcriterion["bullets"]:
                current_subcriterion["bullets"][-1] = clean_line(
                    current_subcriterion["bullets"][-1] + " " + line
                )
            else:
                current_subcriterion["text"] = clean_line(
                    current_subcriterion["text"] + " " + line
                )
        elif current_criterion is not None:
            current_criterion["text"] = clean_line(
                current_criterion["text"] + " " + line
            )

    return criteria


def split_blocks_by_header(lines, header_check):
    blocks = []
    current = None

    for line in lines:
        if header_check(line):
            if current:
                blocks.append(current)
            current = [line]
        elif current is not None:
            current.append(line)

    if current:
        blocks.append(current)

    return blocks


def parse_uf_block(uf_block):
    header = uf_block[0] if uf_block else ""

    number_match = re.search(r"\d+", header)
    number = int(number_match.group(0)) if number_match else 0

    return {
        "number": number,
        "code": extract_uf_code(uf_block),
        "name": normalize_title_case(get_first_value_after_label(uf_block, "Denominación:")),
        "hours": extract_duration(uf_block),
        "criteria": parse_criteria_block(uf_block)
    }


def parse_module_block(module_block):
    """Parse one module and keep its UF block boundaries from swallowing the next module."""
    uf_start = None

    for i, line in enumerate(module_block):
        if is_uf_header(line):
            uf_start = i
            break

    module_info_lines = module_block if uf_start is None else module_block[:uf_start]
    uf_lines = [] if uf_start is None else module_block[uf_start:]

    objective_raw = get_multiline_value_after_label(
        module_info_lines,
        "Asociado a la Unidad de Competencia:",
        [
            r"^Duración:",
            r"^Capacidades y criterios de evaluación",
            r"^UNIDAD FORMATIVA\s+\d+",
            r"^M[ÓO]DULO FORMATIVO\s+\d+",
            r"^M[ÓO]DULO DE PRÁCTICAS"
        ]
    )

    ufs = []

    if uf_lines:
        uf_blocks = split_blocks_by_header(uf_lines, is_uf_header)
        ufs = [parse_uf_block(uf_block) for uf_block in uf_blocks]

    return {
        "code": extract_mf_code(module_info_lines),
        "denomination": normalize_title_case(get_first_value_after_label(module_info_lines, "Denominación:")),
        "duration": extract_duration(module_info_lines),
        "objective": extract_uc_objective(objective_raw),
        "criteria": [] if ufs else parse_criteria_block(module_block),
        "ufs": ufs
    }


def parse_summary_uf(uf_text, number):
    hours = extract_hours(uf_text)

    code_match = re.search(r"(UF\d{4})", uf_text)
    code = code_match.group(1) if code_match else ""

    name = uf_text

    if code:
        name = name.split(code, 1)[1]

    name = re.sub(r"\(\d+\s*horas?\)", "", name, flags=re.IGNORECASE)
    name = clean_line(name)

    return {
        "number": number,
        "code": code,
        "name": normalize_title_case(name),
        "hours": hours,
        "criteria": []
    }


def parse_training_section(text):
    lines = [clean_line(line) for line in text.splitlines() if clean_line(line)]

    start = None

    for i, line in enumerate(lines):
        if "FORMACIÓN DEL CERTIFICADO DE PROFESIONALIDAD" in line:
            start = i
            break

    if start is None:
        return {}

    useful_lines = []

    for line in lines[start + 1:]:
        if is_practice_module_header(line):
            break

        useful_lines.append(line)

    module_blocks = split_blocks_by_header(useful_lines, is_module_header)

    parsed = {}

    for module_block in module_blocks:
        module = parse_module_block(module_block)

        if module["code"]:
            parsed[module["code"]] = module

    return parsed


def valid_uf(uf):
    return bool(
        uf.get("code", "").strip()
        and uf.get("name", "").strip()
        and uf.get("hours", "").strip()
    )


def extract_training_modules(text, modules):
    """Combine summary modules with detailed training-section data from the BOE body."""
    parsed_by_code = parse_training_section(text)
    result = []

    for module in modules:
        module_text = module.get("text", "")

        if not module_text.startswith("MF"):
            continue

        code_match = re.match(r"^(MF\d{4}_\d)", module_text)
        code = code_match.group(1) if code_match else ""

        parsed = parsed_by_code.get(code, {})
        hours = extract_hours(module_text) or parsed.get("duration", "")

        ufs = parsed.get("ufs", [])

        if not ufs:
            ufs = [
                parse_summary_uf(uf_text, index + 1)
                for index, uf_text in enumerate(module.get("ufs", []))
            ]

        ufs = [uf for uf in ufs if valid_uf(uf)]

        result.append({
            "identifier": strip_module_hours(module_text),
            "hours": hours,
            "objective": parsed.get("objective", ""),
            "criteria": parsed.get("criteria", []),
            "ufs": ufs
        })

    return result
