import re
import unicodedata

from source.content_assignment.constants import (
    DOMAIN_SYNONYMS,
    GENERIC_PEDAGOGICAL_TERMS,
    STOPWORDS,
    TECHNICAL_EXPRESSIONS,
)


def strip_accents(text):
    normalized = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def keyword_tokens(text):
    words = re.findall(r"[a-záéíóúüñ0-9]+", strip_accents(text))
    tokens = [
        word
        for word in words
        if len(word) > 2 and word not in STOPWORDS
    ]
    expanded = list(tokens)

    for token in tokens:
        expanded.extend(DOMAIN_SYNONYMS.get(token, []))

    return expanded


def weighted_keywords(text):
    tokens = keyword_tokens(text)
    weights = {}

    for token in tokens:
        token_weight = 0.25 if token in GENERIC_PEDAGOGICAL_TERMS else 1.0
        weights[token] = weights.get(token, 0) + token_weight

    normalized_text = " ".join(tokens)

    for expression in TECHNICAL_EXPRESSIONS:
        if expression in normalized_text:
            weights[expression] = weights.get(expression, 0) + 6.0

    for size, weight in ((2, 2.4), (3, 3.2)):
        for index in range(0, max(len(tokens) - size + 1, 0)):
            phrase = " ".join(tokens[index:index + size])
            weights[phrase] = weights.get(phrase, 0) + weight

    return weights
