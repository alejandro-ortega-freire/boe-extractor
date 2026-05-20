from source.content_assignment.constants import (
    MODALITY_SUPPORTS,
    PRACTICAL_CASE_MARKERS,
    SEMANTIC_CORES,
    VERB_PHASES,
)
from source.content_assignment.tokenizer import (
    keyword_tokens,
    strip_accents,
    weighted_keywords,
)


def bullet_plain_text(bullet):
    parts = [bullet.text]

    for child in bullet.children:
        parts.append(bullet_plain_text(child))

    return " ".join(part for part in parts if part)


def content_segment_text(content, bullet=None):
    parts = [content.title]

    if bullet:
        parts.append(bullet_plain_text(bullet))
    else:
        parts.extend(bullet_plain_text(item) for item in content.bullets)

    return " ".join(part for part in parts if part)


def content_number(content):
    return content.number


def criterion_text(criterion):
    parts = [criterion.text]

    for subcriterion in criterion.subcriteria:
        parts.append(subcriterion.text)
        parts.extend(subcriterion.bullets)

    return " ".join(part for part in parts if part)


def is_practical_case_text(text):
    normalized = strip_accents(text)
    return any(marker in normalized for marker in PRACTICAL_CASE_MARKERS)


def remove_practical_case_boilerplate(text):
    normalized = strip_accents(text)

    for marker in PRACTICAL_CASE_MARKERS:
        marker_index = normalized.find(marker)

        if marker_index >= 0:
            after_marker = text[marker_index + len(marker):]
            return after_marker.lstrip(" ,.:;")

    return text


def merge_weights(target, source, multiplier=1.0):
    for token, weight in source.items():
        target[token] = target.get(token, 0) + (weight * multiplier)


def detect_tags(tokens, taxonomy):
    token_set = set(tokens)
    return {
        name
        for name, values in taxonomy.items()
        if token_set & values
    }


def semantic_signature(text):
    tokens = keyword_tokens(text)
    return {
        "weights": weighted_keywords(text),
        "cores": detect_tags(tokens, SEMANTIC_CORES),
        "phases": detect_tags(tokens, VERB_PHASES),
        "supports": detect_tags(tokens, MODALITY_SUPPORTS),
        "tokens": set(tokens),
    }


def criterion_signature(criterion):
    base_signature = semantic_signature(criterion.text)
    weighted = dict(base_signature["weights"])
    all_text_parts = [criterion.text]

    for subcriterion in criterion.subcriteria:
        subcriterion_text = subcriterion.text
        subcriterion_parts = [subcriterion_text]
        subcriterion_parts.extend(subcriterion.bullets)
        subcriterion_joined = " ".join(part for part in subcriterion_parts if part)

        if is_practical_case_text(subcriterion_text):
            cleaned = remove_practical_case_boilerplate(subcriterion_joined)
            merge_weights(weighted, weighted_keywords(cleaned), 0.45)
            all_text_parts.append(cleaned)
        else:
            merge_weights(weighted, weighted_keywords(subcriterion_joined), 1.0)
            all_text_parts.append(subcriterion_joined)

    full_signature = semantic_signature(" ".join(part for part in all_text_parts if part))
    full_signature["weights"] = weighted
    return full_signature


def content_signature(text):
    return semantic_signature(text)


def semantic_diversity(signatures):
    groups = set()

    for signature in signatures:
        tags = (
            tuple(sorted(signature["cores"])),
            tuple(sorted(signature["phases"])),
            tuple(sorted(signature["supports"])),
        )
        groups.add(tags)

    return len(groups)
