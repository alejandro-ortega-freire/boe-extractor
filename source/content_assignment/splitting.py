from source.content_assignment.constants import (
    MAX_CONTENT_PARTS,
    PARTITION_DIVERSITY_THRESHOLD,
)
from source.content_assignment.scoring import content_match_evaluation
from source.content_assignment.signatures import (
    content_number,
    content_segment_text,
    content_signature,
    semantic_diversity,
)
from source.models import ContentItem


def first_criterion_accepts_intro_fusion(criteria, contents):
    if len(criteria or []) < 2 or len(contents or []) < 2:
        return False

    from source.content_assignment.signatures import criterion_signature

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
