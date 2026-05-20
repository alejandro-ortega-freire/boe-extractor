from source.content_assignment.balancing import (
    ensure_all_segments_assigned,
    rebalance_empty_content_assignments,
    refresh_final_assignment_metadata,
)
from source.content_assignment.constants import ASSIGNMENT_WINDOW
from source.content_assignment.rendering import render_assignments
from source.content_assignment.scoring import score_segment_for_criterion, segment_signature
from source.content_assignment.signatures import content_number, criterion_signature
from source.content_assignment.splitting import (
    first_criterion_accepts_intro_fusion,
    split_content_segments,
)
from source.models import ContentItem, Criterion


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
