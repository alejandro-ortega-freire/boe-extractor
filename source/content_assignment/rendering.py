from source.content_assignment.splitting import clone_content_with_bullets, roman_suffix


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
