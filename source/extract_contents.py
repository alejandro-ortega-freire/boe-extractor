import re
import fitz

from source.cleaning import clean_line
from source.extract_criteria import (
    extract_mf_code,
    extract_uf_code,
    get_page_lines,
    is_module_header,
    is_practice_module_header,
    is_uf_header,
)


CONTROL_BULLET_PREFIX = "\x02\x03"


def is_contents_title(text):
    return text.startswith("Contenidos")


def is_contents_stop_line(text):
    return bool(
        text.startswith("Orientaciones metodológicas")
        or text.startswith("Criterios de acceso")
        or text.startswith("Capacidades y criterios de evaluación")
        or is_module_header(text)
        or is_uf_header(text)
        or is_practice_module_header(text)
    )


def ensure_module(result, current_module):
    if current_module and current_module.get("code"):
        result.setdefault(current_module["code"], {
            "contents": [],
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
                return uf["contents"]

        module_data["ufs"].append({
            "code": current_uf["code"],
            "contents": []
        })

        return module_data["ufs"][-1]["contents"]

    return module_data["contents"]


def new_content_item(title):
    return {
        "title": clean_line(title),
        "bullets": []
    }


def new_bullet(text):
    return {
        "text": clean_line(text),
        "children": []
    }


def get_bullet_match(text):
    return re.match(r"^([-–—○□▫▪◦‣∙\uf0a7])\s*(.*)", text)


def normalize_raw_content_line(text):
    text = str(text).strip()
    has_marker = False

    if text.startswith(CONTROL_BULLET_PREFIX):
        has_marker = True
        text = text[len(CONTROL_BULLET_PREFIX):].strip()

    text = re.sub(r"^[-–—○□▫▪◦‣∙\uf0a7]\s*", "", text).strip()
    return clean_line(text), has_marker


def raw_lines_with_markers(page):
    entries = []

    for raw_line in page.get_text("text").splitlines():
        text, has_marker = normalize_raw_content_line(raw_line)

        if text:
            entries.append({
                "text": text,
                "has_bullet_marker": has_marker
            })

    return entries


def get_content_page_lines(page):
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


def reset_content_state():
    return {
        "current_content": None,
        "current_content_x0": None,
        "bullet_stack": [],
    }


def ends_like_complete_item(text):
    text = clean_line(text)
    return bool(text and text[-1] in ".:;?!)")


def append_text_to_bullet(bullet, text):
    bullet["text"] = clean_line(bullet["text"] + " " + text)


def append_to_last_text(state, text, x0):
    for item in reversed(state["bullet_stack"]):
        if x0 >= item["x0"] - 4:
            append_text_to_bullet(item["bullet"], text)
            return

    if state["bullet_stack"]:
        last = state["bullet_stack"][-1]["bullet"]
        append_text_to_bullet(last, text)
        return

    if state["current_content"] is not None:
        state["current_content"]["title"] = clean_line(
            state["current_content"]["title"] + " " + text
        )


def add_bullet_by_indent(state, text, x0):
    bullet = new_bullet(text)
    stack = state["bullet_stack"]

    while stack and x0 <= stack[-1]["x0"] + 4:
        stack.pop()

    if stack:
        stack[-1]["bullet"]["children"].append(bullet)
    else:
        state["current_content"]["bullets"].append(bullet)

    stack.append({
        "x0": x0,
        "bullet": bullet
    })


def should_continue_previous_bullet(state, x0):
    if not state["bullet_stack"]:
        return False

    current = state["bullet_stack"][-1]

    if abs(x0 - current["x0"]) > 4:
        return False

    return not ends_like_complete_item(current["bullet"]["text"])


def parse_content_line(line, target, state):
    text = clean_line(line["text"])
    x0 = line["x0"]

    if not text:
        return state

    if re.match(r"^\d+\.\s+", text):
        content = new_content_item(text)
        target.append(content)

        state = reset_content_state()
        state["current_content"] = content
        state["current_content_x0"] = x0
        return state

    bullet_match = get_bullet_match(text)
    if bullet_match or line.get("has_bullet_marker"):
        bullet_text = bullet_match.group(2).strip() if bullet_match else text

        if not bullet_text or state["current_content"] is None:
            return state

        add_bullet_by_indent(state, bullet_text, x0)
        return state

    if state["current_content"] is not None:
        content_x0 = state["current_content_x0"]

        if (
            not state["bullet_stack"]
            and content_x0 is not None
            and x0 <= content_x0 + 22
        ):
            state["current_content"]["title"] = clean_line(
                state["current_content"]["title"] + " " + text
            )
            return state

        if (
            content_x0 is not None
            and x0 > content_x0 + 22
            and should_continue_previous_bullet(state, x0)
        ):
            append_to_last_text(state, text, x0)
            return state

        if content_x0 is not None and x0 > content_x0 + 22:
            add_bullet_by_indent(state, text, x0)
            return state

    append_to_last_text(state, text, x0)
    return state


def extract_contents_geometric(pdf_path):
    doc = fitz.open(pdf_path)

    result = {}
    in_training_section = False
    in_contents = False

    current_module = None
    current_uf = None
    state = reset_content_state()

    for page in doc:
        for line in get_content_page_lines(page):
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
                in_contents = False
                current_module = {
                    "code": "",
                    "contents": []
                }
                current_uf = None
                state = reset_content_state()
                continue

            if is_uf_header(text):
                in_contents = False
                current_uf = {
                    "code": "",
                    "contents": []
                }
                state = reset_content_state()
                continue

            if text.startswith("Código:"):
                code = text.replace("Código:", "", 1).strip()
                mf_code = extract_mf_code(code)
                uf_code = extract_uf_code(code)

                if current_uf is not None and uf_code:
                    current_uf["code"] = uf_code
                    ensure_module(result, current_module)

                    module_data = result[current_module["code"]]
                    if not any(uf["code"] == uf_code for uf in module_data["ufs"]):
                        module_data["ufs"].append({
                            "code": uf_code,
                            "contents": []
                        })

                elif current_module is not None and mf_code:
                    current_module["code"] = mf_code
                    ensure_module(result, current_module)

                continue

            if is_contents_title(text):
                in_contents = True
                state = reset_content_state()
                continue

            if is_contents_stop_line(text):
                in_contents = False
                state = reset_content_state()
                continue

            if not in_contents:
                continue

            target = get_current_target(result, current_module, current_uf)

            if target is None:
                continue

            state = parse_content_line(line, target, state)

    return result


def merge_geometric_contents(training_modules, contents_by_module):
    for module in training_modules:
        identifier = module.get("identifier", "")
        mf_match = re.search(r"\bMF\d{4}_\d\b", identifier)

        if not mf_match:
            continue

        mf_code = mf_match.group(0)
        module_contents = contents_by_module.get(mf_code, {})

        if not module_contents:
            continue

        if module.get("ufs"):
            contents_ufs = module_contents.get("ufs", [])

            for uf in module["ufs"]:
                uf_code = uf.get("code", "")

                match = next(
                    (
                        contents_uf
                        for contents_uf in contents_ufs
                        if contents_uf.get("code") == uf_code
                    ),
                    None
                )

                if match:
                    uf["contents"] = match.get("contents", [])
        else:
            module["contents"] = module_contents.get("contents", [])

    return training_modules
