from source.content_assignment.splitting import (
    best_split_candidate,
    split_segment_for_empty_criterion,
)


def rebalance_empty_content_assignments(assigned_segments, criteria_signatures=None):
    """
    Regla prioritaria: si existe contenido oficial disponible, ningún criterio
    debe quedar sin contenido.

    Cuando la similitud semántica deja huecos, primero intenta partir un bloque
    del criterio más adecuado; si no es posible, mueve un segmento desde el
    criterio vecino con más de una asignación. Esta regla pesa más que evitar
    divisiones pequeñas.
    """
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
    """
    Garantiza cobertura total: ningún segmento de contenido oficial puede quedar
    fuera de la asignación final.

    Esta función es el cinturón de seguridad después del scoring semántico. Si
    algún subbloque no fue elegido, se coloca por orden aproximado en el criterio
    esperado para preservar la progresión normal del BOE.
    """
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
    """
    Actualiza la trazabilidad interna cuando el rebalanceo cambia una asignación.

    La salida visible del Word no muestra estos metadatos, pero conservarlos
    ayuda a distinguir asignaciones semánticas fuertes de movimientos de
    cobertura hechos para cumplir las reglas finales.
    """
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
