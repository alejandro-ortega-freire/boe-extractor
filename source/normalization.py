import re
from copy import deepcopy

from source.cleaning import clean_line, dedupe_list


XML_INVALID_PATTERN = re.compile(
    r"[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]"
)

BULLET_MARKER_PATTERN = re.compile(r"^[-–—○□▫▪◦‣∙\uf0a7]\s*")


def normalize_text(value):
    if value is None:
        return ""

    text = str(value)
    text = XML_INVALID_PATTERN.sub("", text)
    text = clean_line(text)
    text = BULLET_MARKER_PATTERN.sub("", text).strip()
    return clean_line(text)


def normalize_text_list(values):
    return dedupe_list(normalize_text(value) for value in values or [])


def normalize_basic_data(data):
    data = data or {}

    return {
        "nombre": normalize_text(data.get("nombre", "")),
        "codigo": normalize_text(data.get("codigo", "")),
        "familia": normalize_text(data.get("familia", "")),
        "nivel": normalize_text(data.get("nivel", "")),
    }


def normalize_modules(modules):
    result = []

    for module in modules or []:
        text = normalize_text(module.get("text", ""))
        ufs = normalize_text_list(module.get("ufs", []))

        if text:
            result.append({
                "text": text,
                "ufs": ufs
            })

    return result


def normalize_bullet_tree(bullets):
    result = []

    for bullet in bullets or []:
        text = normalize_text(bullet.get("text", ""))
        children = normalize_bullet_tree(bullet.get("children", []))

        if text or children:
            result.append({
                "text": text,
                "children": children
            })

    return result


def normalize_contents(contents):
    result = []

    for content in contents or []:
        title = normalize_text(content.get("title", ""))
        bullets = normalize_bullet_tree(content.get("bullets", []))

        if title or bullets:
            result.append({
                "title": title,
                "bullets": bullets
            })

    return result


def normalize_criteria(criteria):
    result = []

    for criterion in criteria or []:
        normalized_criterion = {
            "text": normalize_text(criterion.get("text", "")),
            "subcriteria": []
        }

        for subcriterion in criterion.get("subcriteria", []) or []:
            normalized_subcriterion = {
                "text": normalize_text(subcriterion.get("text", "")),
                "bullets": normalize_text_list(subcriterion.get("bullets", []))
            }

            if normalized_subcriterion["text"] or normalized_subcriterion["bullets"]:
                normalized_criterion["subcriteria"].append(normalized_subcriterion)

        if normalized_criterion["text"] or normalized_criterion["subcriteria"]:
            result.append(normalized_criterion)

    return result


def normalize_training_modules(training_modules):
    result = []

    for module in training_modules or []:
        normalized_module = {
            "identifier": normalize_text(module.get("identifier", "")),
            "hours": normalize_text(module.get("hours", "")),
            "objective": normalize_text(module.get("objective", "")),
            "criteria": normalize_criteria(module.get("criteria", [])),
            "contents": normalize_contents(module.get("contents", [])),
            "ufs": []
        }

        for uf in module.get("ufs", []) or []:
            normalized_uf = {
                "number": uf.get("number", 0),
                "code": normalize_text(uf.get("code", "")),
                "name": normalize_text(uf.get("name", "")),
                "hours": normalize_text(uf.get("hours", "")),
                "criteria": normalize_criteria(uf.get("criteria", [])),
                "contents": normalize_contents(uf.get("contents", [])),
            }

            if normalized_uf["code"] or normalized_uf["name"]:
                normalized_module["ufs"].append(normalized_uf)

        if normalized_module["identifier"] or normalized_module["ufs"]:
            result.append(normalized_module)

    return result


def normalize_equipment_groups(groups):
    result = []
    seen = set()

    for group in groups or []:
        name = normalize_text(group.get("name", ""))
        items = normalize_text_list(group.get("items", []))
        key = (name, tuple(items))

        if name and items and key not in seen:
            result.append({
                "name": name,
                "items": items
            })
            seen.add(key)

    return result


def normalize_document_payload(
    data,
    modules,
    spaces,
    equipment_groups,
    duration_text,
    training_modules
):
    return {
        "data": normalize_basic_data(data),
        "modules": normalize_modules(modules),
        "spaces": normalize_text_list(spaces),
        "equipment_groups": normalize_equipment_groups(equipment_groups),
        "duration_text": normalize_text(duration_text),
        "training_modules": normalize_training_modules(deepcopy(training_modules)),
    }
