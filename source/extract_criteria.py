import re
import fitz

from source.cleaning import clean_line, is_boe_noise


CONTROL_BULLET_PREFIX = "\x02\x03"


def normalize_ce_code(text):
    text = clean_line(text)
    text = re.sub(r"\bCE\s+(\d+\.\d+)", r"CE\1", text)
    text = re.sub(r"\bCE(\d+)\s+(\d+)\b", r"CE\1.\2", text)
    return text


def get_page_lines(page, y_tolerance=3):
    words = []

    for w in page.get_text("words"):
        x0, y0, x1, y1, word, *_ = w

        if is_boe_noise(word):
            continue

        words.append({
            "text": word,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
        })

    words = sorted(words, key=lambda item: (item["y0"], item["x0"]))
    grouped = []

    for word in words:
        placed = False

        for line in grouped:
            if abs(line["y"] - word["y0"]) <= y_tolerance:
                line["words"].append(word)
                placed = True
                break

        if not placed:
            grouped.append({
                "y": word["y0"],
                "words": [word]
            })

    lines = []

    for group in grouped:
        line_words = sorted(group["words"], key=lambda item: item["x0"])
        text = clean_line(" ".join(item["text"] for item in line_words))
        text = normalize_ce_code(text)

        if not text or is_boe_noise(text):
            continue

        lines.append({
            "text": text,
            "x0": min(item["x0"] for item in line_words),
            "y0": min(item["y0"] for item in line_words),
        })

    return sorted(lines, key=lambda item: (item["y0"], item["x0"]))


def normalize_raw_criteria_line(text):
    text = str(text).strip()
    has_marker = False

    if text.startswith(CONTROL_BULLET_PREFIX):
        has_marker = True
        text = text[len(CONTROL_BULLET_PREFIX):].strip()

    text = re.sub(r"^[-–—○□▫▪◦‣∙\uf0a7]\s*", "", text).strip()
    text = normalize_ce_code(text)
    return clean_line(text), has_marker


def raw_lines_with_markers(page):
    entries = []

    for raw_line in page.get_text("text").splitlines():
        text, has_marker = normalize_raw_criteria_line(raw_line)

        if text:
            entries.append({
                "text": text,
                "has_bullet_marker": has_marker
            })

    return entries


def get_criteria_page_lines(page):
    raw_entries = raw_lines_with_markers(page)
    raw_index = 0
    lines = []

    for line in get_page_lines(page):
        line = dict(line)
        line["has_bullet_marker"] = False

        while raw_index < len(raw_entries):
            entry = raw_entries[raw_index]
            raw_index += 1

            if entry["text"] == line["text"]:
                line["has_bullet_marker"] = entry["has_bullet_marker"]
                break

        lines.append(line)

    return lines


def is_module_header(text):
    return bool(re.match(r"^MÓDULO FORMATIVO\s+\d+", text, flags=re.IGNORECASE))


def is_uf_header(text):
    return bool(re.match(r"^UNIDAD FORMATIVA\s+\d+", text, flags=re.IGNORECASE))


def is_practice_module_header(text):
    return bool(re.match(r"^MÓDULO DE PRÁCTICAS", text, flags=re.IGNORECASE))


def is_criteria_title(text):
    return text.startswith("Capacidades y criterios de evaluación")


def is_contents_title(text):
    return text.startswith("Contenidos")


def is_criterion_start(text):
    """Accept C1/C2 starts even when the BOE omits the section title before them."""
    return bool(re.match(r"^C\d+\b:?", text))


def extract_mf_code(text):
    match = re.search(r"\bMF\d{4}_\d\b", text)
    return match.group(0) if match else ""


def extract_uf_code(text):
    match = re.search(r"\bUF\d{4}\b", text)
    return match.group(0) if match else ""


def extract_code_from_line(text):
    if not text.startswith("Código:"):
        return ""

    return text.replace("Código:", "", 1).strip()


def ensure_module(result, current_module):
    if current_module and current_module.get("code"):
        result.setdefault(current_module["code"], {
            "criteria": [],
            "ufs": []
        })


def get_current_target(result, current_module, current_uf):
    if not current_module or not current_module.get("code"):
        return None

    ensure_module(result, current_module)
    module_data = result[current_module["code"]]

    if current_uf and current_uf.get("code"):
        for uf in module_data["ufs"]:
            if uf["code"] == current_uf["code"]:
                return uf["criteria"]

        module_data["ufs"].append({
            "code": current_uf["code"],
            "criteria": []
        })

        return module_data["ufs"][-1]["criteria"]

    return module_data["criteria"]


def parse_criteria_line(
    line,
    target,
    state
):
    """Attach one parsed line to C/CE structures, including CE bullet continuations."""
    text = line["text"]

    if is_criterion_start(text):
        criterion = {
            "text": text,
            "subcriteria": []
        }
        target.append(criterion)

        state["current_criterion"] = criterion
        state["current_subcriterion"] = None
        state["last_bullet"] = None
        state["last_bullet_x"] = None
        return

    if re.match(r"^CE\d+\.\d+", text):
        if state["current_criterion"] is None:
            criterion = {
                "text": "",
                "subcriteria": []
            }
            target.append(criterion)
            state["current_criterion"] = criterion

        subcriterion = {
            "text": text,
            "bullets": []
        }

        state["current_criterion"]["subcriteria"].append(subcriterion)
        state["current_subcriterion"] = subcriterion
        state["last_bullet"] = None
        state["last_bullet_x"] = None
        return

    if text.startswith("-") or line.get("has_bullet_marker"):
        bullet = re.sub(r"^-+\s*", "", text).strip()

        if state["current_subcriterion"] is not None and bullet:
            state["current_subcriterion"]["bullets"].append(bullet)
            state["last_bullet"] = state["current_subcriterion"]["bullets"][-1]
            state["last_bullet_x"] = line["x0"]

        return

    if state["current_subcriterion"] is not None and state["last_bullet"] is not None:
        bullets = state["current_subcriterion"]["bullets"]
        bullets[-1] = clean_line(bullets[-1] + " " + text)
        state["last_bullet"] = bullets[-1]
        return

    state["last_bullet"] = None
    state["last_bullet_x"] = None

    if state["current_subcriterion"] is not None:
        state["current_subcriterion"]["text"] = clean_line(
            state["current_subcriterion"]["text"] + " " + text
        )
        return

    if state["current_criterion"] is not None:
        state["current_criterion"]["text"] = clean_line(
            state["current_criterion"]["text"] + " " + text
        )


def extract_criteria_geometric(pdf_path):
    """Extract criteria from page geometry so UFs survive broken or missing text headings."""
    doc = fitz.open(pdf_path)

    result = {}

    in_training_section = False
    in_criteria = False

    current_module = None
    current_uf = None

    state = {
        "current_criterion": None,
        "current_subcriterion": None,
        "last_bullet": None,
        "last_bullet_x": None,
    }

    for page in doc:
        for line in get_criteria_page_lines(page):
            text = line["text"]

            if "FORMACIÓN DEL CERTIFICADO DE PROFESIONALIDAD" in text:
                in_training_section = True
                continue

            if not in_training_section:
                continue

            if text.startswith("IV. PRESCRIPCIONES"):
                return result

            if is_practice_module_header(text):
                return result

            if is_module_header(text):
                in_criteria = False
                current_module = {
                    "code": "",
                    "criteria": []
                }
                current_uf = None
                state = {
                    "current_criterion": None,
                    "current_subcriterion": None,
                    "last_bullet": None,
                    "last_bullet_x": None,
                }
                continue

            if is_uf_header(text):
                in_criteria = False
                current_uf = {
                    "code": "",
                    "criteria": []
                }
                state = {
                    "current_criterion": None,
                    "current_subcriterion": None,
                    "last_bullet": None,
                    "last_bullet_x": None,
                }
                continue

            if text.startswith("Código:"):
                code = extract_code_from_line(text)

                mf_code = extract_mf_code(code)
                uf_code = extract_uf_code(code)

                if current_uf is not None and uf_code:
                    current_uf["code"] = uf_code
                    ensure_module(result, current_module)

                    module_data = result[current_module["code"]]
                    if not any(uf["code"] == uf_code for uf in module_data["ufs"]):
                        module_data["ufs"].append({
                            "code": uf_code,
                            "criteria": []
                        })

                elif current_module is not None and mf_code:
                    current_module["code"] = mf_code
                    ensure_module(result, current_module)

                continue

            if is_criteria_title(text):
                in_criteria = True
                state = {
                    "current_criterion": None,
                    "current_subcriterion": None,
                    "last_bullet": None,
                    "last_bullet_x": None,
                }
                continue

            if is_contents_title(text):
                in_criteria = False
                state = {
                    "current_criterion": None,
                    "current_subcriterion": None,
                    "last_bullet": None,
                    "last_bullet_x": None,
                }
                continue

            if not in_criteria and is_criterion_start(text):
                target = get_current_target(result, current_module, current_uf)

                if target is not None:
                    in_criteria = True
                    state = {
                        "current_criterion": None,
                        "current_subcriterion": None,
                        "last_bullet": None,
                        "last_bullet_x": None,
                    }
                    parse_criteria_line(line, target, state)
                    continue

            if not in_criteria:
                continue

            target = get_current_target(result, current_module, current_uf)

            if target is None:
                continue

            parse_criteria_line(line, target, state)

    return result


def merge_geometric_criteria(training_modules, criteria_by_module):
    """Prefer geometric criteria when merging them into the normalized training modules."""
    for module in training_modules:
        identifier = module.get("identifier", "")
        mf_match = re.search(r"\bMF\d{4}_\d\b", identifier)

        if not mf_match:
            continue

        mf_code = mf_match.group(0)
        module_criteria = criteria_by_module.get(mf_code, {})

        if not module_criteria:
            continue

        if module.get("ufs"):
            criteria_ufs = module_criteria.get("ufs", [])

            for uf in module["ufs"]:
                uf_code = uf.get("code", "")

                match = next(
                    (
                        criteria_uf
                        for criteria_uf in criteria_ufs
                        if criteria_uf.get("code") == uf_code
                    ),
                    None
                )

                if match:
                    uf["criteria"] = match.get("criteria", [])
        else:
            module["criteria"] = module_criteria.get("criteria", [])

    return training_modules
