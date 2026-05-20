import re
import unicodedata

from source.models import ContentItem, Criterion


SMALL_CONTENT_SPLIT_PENALTY = 4.0
MAX_CONTENT_PARTS = 2
ASSIGNMENT_WINDOW = 1
PARTITION_DIVERSITY_THRESHOLD = 2
MAX_AUTOMATIC_CONTENT_PARTS = 2
FUSION_CORE_BONUS = 3.0
FUSION_SUPPORT_BONUS = 2.0
FUSION_PHASE_BONUS = 1.0
HIGH_CONFIDENCE_THRESHOLD = 14.0
MEDIUM_CONFIDENCE_THRESHOLD = 6.0

STOPWORDS = {
    "a", "al", "ante", "asi", "cada", "como", "con", "contra", "de", "del",
    "desde", "el", "en", "entre", "e", "la", "las", "lo", "los", "o", "para",
    "por", "que", "se", "segun", "sin", "sobre", "su", "sus", "un", "una",
    "unas", "unos", "y",
    "accion", "acciones", "actividad", "actividades", "adecuado", "adecuados",
    "aplicacion", "aplicaciones", "caracteristicas", "caso", "criterio",
    "criterios", "datos", "diferentes", "documento", "documentos", "forma",
    "funcion", "funciones", "informacion", "mediante", "necesario",
    "procedimiento", "procedimientos", "proceso", "procesos", "relacion",
}

GENERIC_PEDAGOGICAL_TERMS = {
    "actividad", "actividades", "aprendizaje", "didactico", "didactica",
    "ensenanza", "formacion", "formativo", "formativa", "metodologia",
    "metodologico", "metodologica", "objetivo", "objetivos", "recurso",
    "recursos", "resultado", "resultados",
}

DOMAIN_SYNONYMS = {
    "email": ["correo", "electronico", "mensaje"],
    "correo": ["email", "electronico", "mensaje", "correspondencia"],
    "correspondencia": ["correo", "mensaje"],
    "mensaje": ["correo", "correspondencia"],
    "ofimatica": ["procesador", "textos", "hoja", "calculo", "presentacion"],
    "procesador": ["texto", "textos", "documento"],
    "textos": ["procesador", "documento", "redaccion"],
    "plantilla": ["modelo", "documento"],
    "plantillas": ["modelo", "documento"],
    "base": ["datos"],
    "datos": ["base", "registro"],
    "hoja": ["calculo"],
    "calculo": ["hoja"],
    "presentacion": ["diapositiva", "grafica"],
    "presentaciones": ["diapositiva", "grafica"],
    "archivo": ["fichero", "carpeta"],
    "archivos": ["ficheros", "carpetas"],
    "carpeta": ["archivo", "fichero"],
    "carpetas": ["archivos", "ficheros"],
    "seguridad": ["confidencialidad", "integridad", "proteccion"],
    "urgencia": ["emergencia"],
    "urgencias": ["emergencias"],
    "emergencia": ["urgencia"],
    "emergencias": ["urgencias"],
}

TECHNICAL_EXPRESSIONS = {
    "aula virtual",
    "base datos",
    "bases datos",
    "calidad acciones",
    "carta presentacion",
    "correo electronico",
    "curriculum vitae",
    "entorno virtual",
    "escala likert",
    "firma electronica",
    "hoja calculo",
    "hojas calculo",
    "lista cotejo",
    "plan tutorial",
    "pizarra digital",
    "procesador textos",
    "programacion didactica",
    "prueba practica",
    "prueba teorica",
    "registro calificaciones",
    "soporte vital",
    "soporte vital avanzado",
    "soporte vital basico",
    "sistema operativo",
    "tabla especificaciones",
    "tratamiento textos",
}

SEMANTIC_CORES = {
    "programacion": {"programacion", "didactica", "temporalizacion", "unidad", "cronograma"},
    "evaluacion": {"evaluacion", "prueba", "pruebas", "item", "items", "rubrica", "cotejo", "escala", "calificacion"},
    "fundamentos": {"estructura", "estructuras", "normativa", "marco", "sistema", "certificado", "certificados", "fundamento", "fundamentos"},
    "tutoria": {"tutoria", "tutorial", "seguimiento", "alumno", "alumnos", "orientacion", "asesoramiento"},
    "material": {"material", "materiales", "grafico", "graficos", "multimedia", "impreso", "presentacion"},
    "virtual": {"virtual", "online", "linea", "foro", "foros", "chat", "videotutorial", "plataforma"},
    "correo": {"correo", "electronico", "mensaje", "correspondencia"},
    "ofimatica": {"procesador", "textos", "calculo", "presentacion", "archivo", "carpeta"},
    "calidad": {"calidad", "innovacion", "actualizacion", "mejora", "revision"},
    "empleo": {"empleo", "curriculum", "entrevista", "profesional", "ocupacion", "competencia"},
    "seguridad": {"seguridad", "prevencion", "riesgos", "proteccion", "confidencialidad"},
}

VERB_PHASES = {
    "conceptual": {
        "analizar", "clasificar", "definir", "describir", "diferenciar",
        "enumerar", "identificar", "indicar", "reconocer",
    },
    "production": {
        "adaptar", "construir", "disenar", "elaborar", "organizar",
        "redactar", "seleccionar", "secuenciar",
    },
    "use": {
        "aplicar", "comprobar", "manejar", "registrar", "supervisar",
        "ubicar", "utilizar",
    },
    "evaluation": {
        "actualizar", "corregir", "evaluar", "mejorar", "perfeccionar",
        "proponer", "revisar",
    },
    "support": {
        "asesorar", "fomentar", "orientar", "promover", "tutorizar",
    },
}

MODALITY_SUPPORTS = {
    "presencial": {"presencial", "aula"},
    "online": {"online", "linea", "virtual", "plataforma", "foro", "chat", "videotutorial"},
    "graphic": {"grafico", "graficos", "imagen", "imagenes", "tipografia", "reticula"},
    "multimedia": {"multimedia", "diapositiva", "sonido", "animacion", "hipervinculo"},
    "text": {"texto", "textos", "procesador", "redaccion", "documento"},
}

NEGATIVE_KEYWORD_GROUPS = [
    {"correo", "electronico", "mensaje", "correspondencia"},
    {"texto", "textos", "procesador", "redaccion", "plantilla", "plantillas"},
    {"calculo", "hoja", "hojas"},
    {"base", "bases", "datos", "registro", "registros"},
    {"presentacion", "presentaciones", "diapositiva", "grafica", "graficas"},
    {"archivo", "archivos", "fichero", "ficheros", "carpeta", "carpetas"},
    {"seguridad", "confidencialidad", "integridad", "proteccion"},
    {"urgencia", "urgencias", "emergencia", "emergencias"},
]

PRACTICAL_CASE_MARKERS = (
    "en un supuesto practico",
    "ante un supuesto practico",
    "a partir de un supuesto practico",
)


def contains_model_items(values, model_type):
    return any(isinstance(value, model_type) for value in values or [])


def criteria_to_models(criteria):
    return [
        criterion if isinstance(criterion, Criterion) else Criterion.from_dict(criterion)
        for criterion in criteria or []
    ]


def contents_to_models(contents):
    return [
        content if isinstance(content, ContentItem) else ContentItem.from_dict(content)
        for content in contents or []
    ]


def content_assignments_to_dicts(assignments):
    return [
        [
            content.to_dict() if isinstance(content, ContentItem) else content
            for content in contents
        ]
        for contents in assignments
    ]


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


def first_criterion_accepts_intro_fusion(criteria, contents):
    if len(criteria or []) < 2 or len(contents or []) < 2:
        return False

    first_criterion = criterion_signature(criteria[0])
    first_content = content_signature(content_segment_text(contents[0]))
    second_content = content_signature(content_segment_text(contents[1]))
    intro_cores = {"fundamentos", "empleo"}
    specific_cores = {
        "calidad", "correo", "evaluacion", "material", "ofimatica",
        "seguridad", "tutoria",
    }

    return (
        "conceptual" in first_criterion["phases"]
        and bool(first_criterion["cores"] & intro_cores)
        and not bool(first_criterion["cores"] & specific_cores)
        and bool(first_content["cores"] & intro_cores)
        and bool(second_content["cores"] & intro_cores)
    )


def should_split_content(content, contents, criterion_count):
    return False


def content_is_partible(content):
    bullets = content.bullets

    if len(bullets) < 2:
        return False

    signatures = [
        content_signature(content_segment_text(content, bullet))
        for bullet in bullets
    ]
    diverse_groups = semantic_diversity(signatures)
    tagged_groups = sum(
        1
        for signature in signatures
        if signature["cores"] or signature["phases"] or signature["supports"]
    )

    return (
        diverse_groups >= PARTITION_DIVERSITY_THRESHOLD
        and tagged_groups >= PARTITION_DIVERSITY_THRESHOLD
    )


def overlap_score(left, right, weight):
    return len(left & right) * weight


def confidence_from_score(score, reasons):
    if score >= HIGH_CONFIDENCE_THRESHOLD and any(
        reason.startswith("core:")
        or reason.startswith("technical:")
        for reason in reasons
    ):
        return "high"

    if score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"

    return "low"


def shared_weighted_terms(criteria_weights, content_weights, minimum_weight=2.0):
    terms = []

    for token, content_weight in content_weights.items():
        if token not in criteria_weights:
            continue

        shared_weight = min(content_weight, criteria_weights[token])

        if shared_weight >= minimum_weight:
            terms.append((token, shared_weight))

    return sorted(terms, key=lambda item: (-item[1], item[0]))


def content_match_evaluation(criteria_signature, text):
    content_sig = content_signature(text)
    criteria_weights = criteria_signature["weights"]
    content_weights = content_sig["weights"]

    if not criteria_weights or not content_weights:
        return {
            "score": 0.0,
            "confidence": "low",
            "reasons": ["no-comparable-keywords"],
            "content_signature": content_sig,
        }

    keyword_score = sum(
        min(weight, criteria_weights.get(token, 0))
        for token, weight in content_weights.items()
    )
    core_overlap = criteria_signature["cores"] & content_sig["cores"]
    phase_overlap = criteria_signature["phases"] & content_sig["phases"]
    support_overlap = criteria_signature["supports"] & content_sig["supports"]
    core_score = overlap_score(criteria_signature["cores"], content_sig["cores"], 8.0)
    phase_score = overlap_score(criteria_signature["phases"], content_sig["phases"], 4.0)
    support_score = overlap_score(criteria_signature["supports"], content_sig["supports"], 3.0)
    positive_score = keyword_score + core_score + phase_score + support_score
    generic_overlap = criteria_signature["tokens"] & content_sig["tokens"] & GENERIC_PEDAGOGICAL_TERMS

    criteria_tokens = set(criteria_weights)
    content_tokens = set(content_weights)
    negative_penalty = 0.0
    reasons = []

    if core_overlap:
        reasons.extend(f"core:{item}" for item in sorted(core_overlap))

    if phase_overlap:
        reasons.extend(f"phase:{item}" for item in sorted(phase_overlap))

    if support_overlap:
        reasons.extend(f"support:{item}" for item in sorted(support_overlap))

    for term, _weight in shared_weighted_terms(criteria_weights, content_weights):
        reason_prefix = "technical" if term in TECHNICAL_EXPRESSIONS else "term"
        reasons.append(f"{reason_prefix}:{term}")

    for group in NEGATIVE_KEYWORD_GROUPS:
        if criteria_tokens & group:
            continue

        if content_tokens & group:
            negative_penalty += 1.5
            reasons.append("penalty:foreign-domain")

    if (
        generic_overlap
        and not (criteria_signature["cores"] & content_sig["cores"])
        and not (criteria_signature["phases"] & content_sig["phases"])
        and not (criteria_signature["supports"] & content_sig["supports"])
    ):
        negative_penalty += len(generic_overlap) * 1.25
        reasons.append("penalty:generic-only")

    final_score = positive_score - negative_penalty
    confidence = confidence_from_score(final_score, reasons)

    return {
        "score": final_score,
        "confidence": confidence,
        "reasons": reasons or ["order-fallback"],
        "content_signature": content_sig,
        "components": {
            "keyword": keyword_score,
            "core": core_score,
            "phase": phase_score,
            "support": support_score,
            "penalty": negative_penalty,
        },
    }


def content_similarity(criteria_signature, text):
    return content_match_evaluation(criteria_signature, text)["score"]


def segment_signature(segment):
    if "signature" not in segment:
        segment["signature"] = content_signature(segment["text"])

    return segment["signature"]


def consecutive_fusion_bonus(candidate_segments, segment):
    if not candidate_segments:
        return 0.0

    previous_signature = segment_signature(candidate_segments[-1])
    current_signature = segment_signature(segment)
    bonus = 0.0

    bonus += overlap_score(previous_signature["cores"], current_signature["cores"], FUSION_CORE_BONUS)
    bonus += overlap_score(previous_signature["supports"], current_signature["supports"], FUSION_SUPPORT_BONUS)
    bonus += overlap_score(previous_signature["phases"], current_signature["phases"], FUSION_PHASE_BONUS)

    return bonus


def score_segment_for_criterion(criteria_signature, assigned_segments, segment, expected, criterion_index):
    evaluation = content_match_evaluation(criteria_signature, segment["text"])
    fusion_bonus = consecutive_fusion_bonus(assigned_segments, segment)
    order_penalty = abs(criterion_index - expected) * 1.25
    split_penalty = SMALL_CONTENT_SPLIT_PENALTY if segment.get("is_split") else 0
    score = evaluation["score"] + fusion_bonus - order_penalty - split_penalty

    reasons = list(evaluation["reasons"])

    if fusion_bonus:
        reasons.append("bonus:consecutive-fusion")

    if order_penalty:
        reasons.append("penalty:order-distance")

    if split_penalty:
        reasons.append("penalty:split-segment")

    return {
        "score": score,
        "base_score": evaluation["score"],
        "confidence": confidence_from_score(score, reasons),
        "reasons": reasons,
        "components": {
            **evaluation.get("components", {}),
            "fusion_bonus": fusion_bonus,
            "order_penalty": order_penalty,
            "split_penalty": split_penalty,
        },
    }


def clone_content_with_bullets(content, bullets, suffix="", assignment=None):
    title = content.title

    if suffix and title:
        title = f"{title} ({suffix})"

    cloned = ContentItem(title=title, bullets=list(bullets or []))
    cloned.assignment = assignment or {}
    return cloned


def split_bullets_into_chunks(bullets, max_parts, allow_extra_parts=False):
    total = len(bullets)

    if total <= 1:
        return [bullets]

    part_limit = total if allow_extra_parts else MAX_CONTENT_PARTS
    parts = min(max_parts, part_limit, total)

    if parts < 2:
        return [bullets]

    base_size = total // parts
    remainder = total % parts
    chunks = []
    start = 0

    for index in range(parts):
        size = base_size + (1 if index < remainder else 0)
        end = start + size
        chunks.append(bullets[start:end])
        start = end

    return chunks


def split_content_segments(contents, criterion_count=1):
    segments = []

    for content_index, content in enumerate(contents or []):
        bullets = content.bullets

        if bullets and should_split_content(content, contents, criterion_count):
            chunks = split_bullets_into_chunks(bullets, criterion_count)
            bullet_start = 0

            for chunk in chunks:
                segments.append({
                    "content_index": content_index,
                    "bullet_index": bullet_start,
                    "content": content,
                    "bullets": chunk,
                    "is_split": len(chunks) > 1,
                    "text": " ".join(
                        content_segment_text(content, bullet)
                        for bullet in chunk
                    ),
                })
                bullet_start += len(chunk)
        else:
            segments.append({
                "content_index": content_index,
                "bullet_index": 0,
                "content": content,
                "bullets": content.bullets,
                "is_split": False,
                "text": content_segment_text(content),
            })

    return segments


def split_content_segments_for_coverage(contents):
    segments = []

    for content_index, content in enumerate(contents or []):
        bullets = content.bullets

        if bullets:
            chunks = split_bullets_into_chunks(
                bullets,
                max(len(bullets), 1),
                allow_extra_parts=True
            )
            bullet_start = 0

            for chunk in chunks:
                segments.append({
                    "content_index": content_index,
                    "bullet_index": bullet_start,
                    "content": content,
                    "bullets": chunk,
                    "is_split": len(chunks) > 1,
                    "text": " ".join(
                        content_segment_text(content, bullet)
                        for bullet in chunk
                    ),
                })
                bullet_start += len(chunk)
        else:
            segments.append({
                "content_index": content_index,
                "bullet_index": 0,
                "content": content,
                "bullets": content.bullets,
                "is_split": False,
                "text": content_segment_text(content),
            })

    return segments


def roman_suffix(index):
    suffixes = ["I", "II", "III", "IV", "V", "VI"]
    return suffixes[index] if index < len(suffixes) else str(index + 1)


def split_segment_for_empty_criterion(segment, empty_index, donor_index):
    bullets = segment.get("bullets", [])

    if len(bullets) <= 1:
        return None

    if empty_index < donor_index:
        empty_bullets = bullets[:max(1, len(bullets) // 2)]
        donor_bullets = bullets[len(empty_bullets):]
        empty_bullet_index = segment["bullet_index"]
        donor_bullet_index = segment["bullet_index"] + len(empty_bullets)
    else:
        donor_bullets = bullets[:max(1, len(bullets) // 2)]
        empty_bullets = bullets[len(donor_bullets):]
        donor_bullet_index = segment["bullet_index"]
        empty_bullet_index = segment["bullet_index"] + len(donor_bullets)

    if not donor_bullets or not empty_bullets:
        return None

    segment["bullets"] = donor_bullets
    segment["bullet_index"] = donor_bullet_index
    segment["is_split"] = True
    segment["text"] = " ".join(
        content_segment_text(segment["content"], bullet)
        for bullet in donor_bullets
    )
    segment.pop("signature", None)

    return {
        **segment,
        "bullets": empty_bullets,
        "bullet_index": empty_bullet_index,
        "is_split": True,
        "text": " ".join(
            content_segment_text(segment["content"], bullet)
            for bullet in empty_bullets
        ),
    }


def best_split_candidate(assigned_segments, criteria_signatures, empty_index):
    best = None

    for donor_index, criterion_segments in enumerate(assigned_segments):
        if donor_index == empty_index:
            continue

        for segment_index, segment in enumerate(criterion_segments):
            if len(segment.get("bullets", [])) <= 1:
                continue

            candidate_segment = split_segment_preview(segment, empty_index, donor_index)

            if not candidate_segment:
                continue

            evaluation = content_match_evaluation(criteria_signatures[empty_index], candidate_segment["text"])
            distance_penalty = abs(donor_index - empty_index) * 0.75
            score = evaluation["score"] - distance_penalty
            segment_number = content_number(segment["content"])

            if segment_number and segment_number - 1 == empty_index:
                score += 14.0

            if segment_number and segment_number == len(assigned_segments) and empty_index >= segment_number - 2:
                score += 8.0

            if best is None or score > best["score"]:
                best = {
                    "score": score,
                    "donor_index": donor_index,
                    "segment_index": segment_index,
                }

    return best


def split_segment_preview(segment, empty_index, donor_index):
    bullets = segment.get("bullets", [])

    if len(bullets) <= 1:
        return None

    if empty_index < donor_index:
        empty_bullets = bullets[:max(1, len(bullets) // 2)]
        empty_bullet_index = segment["bullet_index"]
    else:
        donor_bullets = bullets[:max(1, len(bullets) // 2)]
        empty_bullets = bullets[len(donor_bullets):]
        empty_bullet_index = segment["bullet_index"] + len(donor_bullets)

    if not empty_bullets:
        return None

    return {
        **segment,
        "bullets": empty_bullets,
        "bullet_index": empty_bullet_index,
        "is_split": True,
        "text": " ".join(
            content_segment_text(segment["content"], bullet)
            for bullet in empty_bullets
        ),
    }


def rebalance_empty_content_assignments(assigned_segments, criteria_signatures=None):
    if not assigned_segments:
        return assigned_segments

    while True:
        empty_indexes = [
            index
            for index, segments in enumerate(assigned_segments)
            if not segments
        ]

        if not empty_indexes:
            break

        empty_index = empty_indexes[0]
        split_candidate = (
            best_split_candidate(assigned_segments, criteria_signatures, empty_index)
            if criteria_signatures
            else None
        )

        if split_candidate:
            donor_index = split_candidate["donor_index"]
            segment_index = split_candidate["segment_index"]
            new_segment = split_segment_for_empty_criterion(
                assigned_segments[donor_index][segment_index],
                empty_index,
                donor_index,
            )

            if new_segment:
                assigned_segments[empty_index].append(new_segment)
                continue

        donors = [
            index
            for index, segments in enumerate(assigned_segments)
            if len(segments) > 1
        ]

        if not donors:
            break

        donor_index = min(
            donors,
            key=lambda index: (abs(index - empty_index), index > empty_index)
        )

        if donor_index < empty_index:
            segment = assigned_segments[donor_index].pop()
        else:
            segment = assigned_segments[donor_index].pop(0)

        assigned_segments[empty_index].append(segment)

    return assigned_segments


def ensure_all_segments_assigned(assigned_segments, segments):
    assigned_ids = {
        id(segment)
        for criterion_segments in assigned_segments
        for segment in criterion_segments
    }
    missing_segments = [
        segment
        for segment in segments
        if id(segment) not in assigned_ids
    ]

    if not missing_segments:
        return assigned_segments

    content_count = max(len({item["content_index"] for item in segments}), 1)

    for segment in missing_segments:
        expected = round(len(assigned_segments) * segment["content_index"] / content_count)
        target_index = min(expected, len(assigned_segments) - 1)
        assigned_segments[target_index].append(segment)

    return assigned_segments


def refresh_final_assignment_metadata(assigned_segments):
    for criterion_index, criterion_segments in enumerate(assigned_segments):
        for segment in criterion_segments:
            assignment = segment.setdefault("assignment", {})

            if assignment.get("criterion_index") != criterion_index:
                reasons = list(assignment.get("reasons", []))
                reasons.append("fallback:coverage-rebalance")
                assignment["reasons"] = reasons
                assignment["confidence"] = "low"

            assignment["criterion_index"] = criterion_index

    return assigned_segments


def summarize_assignments(assignments):
    if not assignments:
        return {}

    confidence_rank = {"low": 0, "medium": 1, "high": 2}
    weakest_confidence = min(
        (assignment.get("confidence", "low") for assignment in assignments),
        key=lambda value: confidence_rank.get(value, 0),
    )
    reasons = []

    for assignment in assignments:
        for reason in assignment.get("reasons", []):
            if reason not in reasons:
                reasons.append(reason)

    return {
        "confidence": weakest_confidence,
        "score": round(
            sum(assignment.get("score", 0.0) for assignment in assignments) / len(assignments),
            3,
        ),
        "reasons": reasons,
        "segments": assignments,
    }


def assign_segments_to_criteria(criteria, segments, use_content_numbers=True):
    assigned_segments = [[] for _ in criteria]

    if not segments:
        return assigned_segments

    criteria_signatures = [criterion_signature(criterion) for criterion in criteria]
    min_criterion_index = 0
    enough_segments_for_criteria = len(segments) >= len(criteria)

    for segment_index, segment in enumerate(segments):
        segment_number = content_number(segment["content"]) if use_content_numbers else None
        if not enough_segments_for_criteria and segment_index == len(segments) - 1:
            expected = len(criteria) - 1
        elif segment_number:
            expected = min(segment_number - 1, len(criteria) - 1)
        else:
            expected = round(
                segment_index * (len(criteria) - 1) / max(len(segments) - 1, 1)
            )
        best_index = min_criterion_index
        best_score = None

        if enough_segments_for_criteria:
            lower_bound = max(min_criterion_index, expected - ASSIGNMENT_WINDOW)
        elif segment_number:
            lower_bound = max(min_criterion_index, expected)
        else:
            lower_bound = max(min_criterion_index, expected - ASSIGNMENT_WINDOW)
        upper_bound = min(len(criteria) - 1, expected + ASSIGNMENT_WINDOW)

        if lower_bound > upper_bound:
            lower_bound = min_criterion_index
            upper_bound = min(len(criteria) - 1, min_criterion_index + ASSIGNMENT_WINDOW)

        for criterion_index in range(lower_bound, upper_bound + 1):
            evaluation = score_segment_for_criterion(
                criteria_signatures[criterion_index],
                assigned_segments[criterion_index],
                segment,
                expected,
                criterion_index,
            )
            score = evaluation["score"]
            if criterion_index == expected:
                score += 18.0
            if (
                criterion_index == len(criteria) - 1
                and segment_index < len(segments) - 1
            ):
                current_signature = segment_signature(segment)
                next_signature = segment_signature(segments[segment_index + 1])

                if "online" not in current_signature["supports"] and "online" in next_signature["supports"]:
                    score -= 25.0

            if best_score is None or score > best_score:
                best_score = score
                best_index = criterion_index
                best_evaluation = evaluation

        segment["assignment"] = {
            "criterion_index": best_index,
            "score": round(best_evaluation["score"], 3),
            "base_score": round(best_evaluation["base_score"], 3),
            "confidence": best_evaluation["confidence"],
            "reasons": best_evaluation["reasons"],
            "components": best_evaluation["components"],
        }
        assigned_segments[best_index].append(segment)
        min_criterion_index = best_index

    assigned_segments = ensure_all_segments_assigned(assigned_segments, segments)
    assigned_segments = rebalance_empty_content_assignments(assigned_segments, criteria_signatures)
    assigned_segments = ensure_all_segments_assigned(assigned_segments, segments)
    assigned_segments = refresh_final_assignment_metadata(assigned_segments)

    return assigned_segments


def build_contents_from_segments(contents, segments, part_positions=None, criterion_index=0):
    if not segments:
        return []

    part_positions = part_positions or {}
    content_indices_in_parts = {}

    for segment in segments:
        content_indices_in_parts.setdefault(segment["content_index"], []).append(segment)

    result = []

    for content_index in sorted(content_indices_in_parts):
        grouped = sorted(
            content_indices_in_parts[content_index],
            key=lambda item: item["bullet_index"]
        )
        content = grouped[0]["content"]
        suffix = ""

        if content_index in part_positions:
            suffix = roman_suffix(part_positions[content_index].index(criterion_index))

        bullets = []
        assignments = []
        for segment in grouped:
            bullets.extend(segment["bullets"])
            if segment.get("assignment"):
                assignments.append(segment["assignment"])

        result.append(clone_content_with_bullets(
            content,
            bullets,
            suffix,
            summarize_assignments(assignments),
        ))

    return result


def render_assignments(contents, assigned_segments):
    part_positions = {}
    all_content_indexes = {
        segment["content_index"]
        for criterion_segments in assigned_segments
        for segment in criterion_segments
    }

    for content_index in sorted(all_content_indexes):
        positions = [
            criterion_index
            for criterion_index, criterion_segments in enumerate(assigned_segments)
            if any(segment["content_index"] == content_index for segment in criterion_segments)
        ]
        if len(positions) > 1:
            part_positions[content_index] = positions

    return [
        build_contents_from_segments(
            contents,
            segments_for_criterion,
            part_positions,
            criterion_index
        )
        for criterion_index, segments_for_criterion in enumerate(assigned_segments)
    ]


def assign_content_models_to_criteria(criteria, contents):
    if not criteria:
        return []

    if len(criteria) == 1:
        return [contents or []]

    if first_criterion_accepts_intro_fusion(criteria, contents):
        remaining_segments = split_content_segments(contents[2:], len(criteria) - 1)
        remaining_assigned = assign_segments_to_criteria(
            criteria[1:],
            remaining_segments,
            use_content_numbers=False,
        )
        return [
            [contents[0], contents[1]],
            *render_assignments(contents[2:], remaining_assigned),
        ]

    segments = split_content_segments(contents, len(criteria))
    assigned_segments = assign_segments_to_criteria(criteria, segments)
    return render_assignments(contents, assigned_segments)


def assign_contents_to_criteria(criteria, contents):
    """Assign official contents to criteria while preserving model/dict caller compatibility."""
    return_models = (
        contains_model_items(criteria, Criterion)
        or contains_model_items(contents, ContentItem)
    )
    criteria_models = criteria_to_models(criteria)
    content_models = contents_to_models(contents)
    assignments = assign_content_models_to_criteria(criteria_models, content_models)

    if return_models:
        return assignments

    return content_assignments_to_dicts(assignments)
