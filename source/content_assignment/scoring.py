from source.content_assignment.constants import (
    FUSION_CORE_BONUS,
    FUSION_PHASE_BONUS,
    FUSION_SUPPORT_BONUS,
    GENERIC_PEDAGOGICAL_TERMS,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    NEGATIVE_KEYWORD_GROUPS,
    SMALL_CONTENT_SPLIT_PENALTY,
    TECHNICAL_EXPRESSIONS,
)
from source.content_assignment.signatures import content_signature


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
