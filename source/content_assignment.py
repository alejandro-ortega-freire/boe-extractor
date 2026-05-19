import re
import unicodedata


SMALL_CONTENT_SPLIT_PENALTY = 4.0
MAX_CONTENT_PARTS = 2
ASSIGNMENT_WINDOW = 1

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
        weights[token] = weights.get(token, 0) + 1.0

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
    parts = [bullet.get("text", "")]

    for child in bullet.get("children", []):
        parts.append(bullet_plain_text(child))

    return " ".join(part for part in parts if part)


def content_segment_text(content, bullet=None):
    parts = [content.get("title", "")]

    if bullet:
        parts.append(bullet_plain_text(bullet))
    else:
        parts.extend(bullet_plain_text(item) for item in content.get("bullets", []))

    return " ".join(part for part in parts if part)


def criterion_text(criterion):
    parts = [criterion.get("text", "")]

    for subcriterion in criterion.get("subcriteria", []):
        parts.append(subcriterion.get("text", ""))
        parts.extend(subcriterion.get("bullets", []))

    return " ".join(part for part in parts if part)


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
    return semantic_signature(criterion_text(criterion))


def content_signature(text):
    return semantic_signature(text)


def overlap_score(left, right, weight):
    return len(left & right) * weight


def content_similarity(criteria_signature, text):
    content_sig = content_signature(text)
    criteria_weights = criteria_signature["weights"]
    content_weights = content_sig["weights"]

    if not criteria_weights or not content_weights:
        return 0.0

    positive_score = sum(
        min(weight, criteria_weights.get(token, 0))
        for token, weight in content_weights.items()
    )
    positive_score += overlap_score(criteria_signature["cores"], content_sig["cores"], 8.0)
    positive_score += overlap_score(criteria_signature["phases"], content_sig["phases"], 4.0)
    positive_score += overlap_score(criteria_signature["supports"], content_sig["supports"], 3.0)

    criteria_tokens = set(criteria_weights)
    content_tokens = set(content_weights)
    negative_penalty = 0.0

    for group in NEGATIVE_KEYWORD_GROUPS:
        if criteria_tokens & group:
            continue

        if content_tokens & group:
            negative_penalty += 1.5

    return positive_score - negative_penalty


def clone_content_with_bullets(content, bullets, suffix=""):
    title = content.get("title", "")

    if suffix and title:
        title = f"{title} ({suffix})"

    return {
        "title": title,
        "bullets": bullets,
    }


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
        bullets = content.get("bullets", [])

        if bullets:
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
                "bullets": [],
                "is_split": False,
                "text": content_segment_text(content),
            })

    if len(segments) < criterion_count:
        fallback_segments = split_content_segments_for_coverage(contents)

        if len(fallback_segments) > len(segments):
            return fallback_segments

    return segments


def split_content_segments_for_coverage(contents):
    segments = []

    for content_index, content in enumerate(contents or []):
        bullets = content.get("bullets", [])

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
                "bullets": [],
                "is_split": False,
                "text": content_segment_text(content),
            })

    return segments


def roman_suffix(index):
    suffixes = ["I", "II", "III", "IV", "V", "VI"]
    return suffixes[index] if index < len(suffixes) else str(index + 1)


def rebalance_empty_content_assignments(assigned_segments):
    if not assigned_segments:
        return assigned_segments

    empty_indexes = [
        index
        for index, segments in enumerate(assigned_segments)
        if not segments
    ]

    for empty_index in empty_indexes:
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


def assign_segments_to_criteria(criteria, segments):
    assigned_segments = [[] for _ in criteria]

    if not segments:
        return assigned_segments

    criteria_signatures = [criterion_signature(criterion) for criterion in criteria]
    min_criterion_index = 0

    for segment_index, segment in enumerate(segments):
        expected = round(
            segment_index * (len(criteria) - 1) / max(len(segments) - 1, 1)
        )
        best_index = min_criterion_index
        best_score = None

        lower_bound = max(min_criterion_index, expected - ASSIGNMENT_WINDOW)
        upper_bound = min(len(criteria) - 1, expected + ASSIGNMENT_WINDOW)

        if lower_bound > upper_bound:
            lower_bound = min_criterion_index
            upper_bound = min(len(criteria) - 1, min_criterion_index + ASSIGNMENT_WINDOW)

        for criterion_index in range(lower_bound, upper_bound + 1):
            similarity = content_similarity(criteria_signatures[criterion_index], segment["text"])
            order_penalty = abs(criterion_index - expected) * 1.25
            split_penalty = SMALL_CONTENT_SPLIT_PENALTY if segment.get("is_split") else 0
            score = similarity - order_penalty - split_penalty

            if best_score is None or score > best_score:
                best_score = score
                best_index = criterion_index

        assigned_segments[best_index].append(segment)
        min_criterion_index = best_index

    assigned_segments = ensure_all_segments_assigned(assigned_segments, segments)
    assigned_segments = rebalance_empty_content_assignments(assigned_segments)
    assigned_segments = ensure_all_segments_assigned(assigned_segments, segments)

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
        for segment in grouped:
            bullets.extend(segment["bullets"])

        result.append(clone_content_with_bullets(content, bullets, suffix))

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


def assign_contents_to_criteria(criteria, contents):
    if not criteria:
        return []

    if len(criteria) == 1:
        return [contents or []]

    segments = split_content_segments(contents, len(criteria))
    assigned_segments = assign_segments_to_criteria(criteria, segments)
    return render_assignments(contents, assigned_segments)
