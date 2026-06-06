import re

from source.schedule import code_from_text, format_date, parse_hours


def evaluation_blocks(module):
    return getattr(module, "ufs", None) or [module]


def hours_value(value):
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def evaluable_activity_count(hours):
    if hours <= 30:
        return 1
    if hours <= 50:
        return 2
    if hours <= 90:
        return 3
    if hours <= 120:
        return 4
    return 5


def block_code(block):
    if isinstance(block, str):
        return code_from_text(block)

    return (
        getattr(block, "code", "")
        or code_from_text(getattr(block, "identifier", ""))
        or code_from_text(getattr(block, "text", ""))
    )


def module_hours(module):
    explicit_hours = getattr(module, "hours", "")

    if explicit_hours:
        return hours_value(explicit_hours)

    text = getattr(module, "text", "") or getattr(module, "identifier", "")
    parsed_hours = parse_hours(text)

    if parsed_hours:
        return parsed_hours

    return hours_value(
        text
    )


def sessions_for_block(schedule, block):
    code = block_code(block)

    if not schedule or not code:
        return []

    return list(schedule.get("dates_by_code", {}).get(code, {}).get("sessions", []))


def module_sessions(module, schedule):
    sessions = []
    session_number_by_date = {}

    for block in evaluation_blocks(module):
        code = block_code(block)

        for session in sessions_for_block(schedule, block):
            item = dict(session)
            item["block_code"] = code
            sessions.append(item)

    sessions = sorted(sessions, key=lambda item: item["session_number"])

    for item in sessions:
        day = item["date"]

        if day not in session_number_by_date:
            session_number_by_date[day] = len(session_number_by_date) + 1

        item["module_session_number"] = session_number_by_date[day]

    return sessions


def select_evenly(items, count):
    if count <= 0 or not items:
        return []

    if count >= len(items):
        return list(items)

    selected = []
    used_indexes = set()

    for number in range(1, count + 1):
        index = round(number * (len(items) + 1) / (count + 1)) - 1
        index = max(0, min(index, len(items) - 1))

        while index in used_indexes and index + 1 < len(items):
            index += 1

        while index in used_indexes and index > 0:
            index -= 1

        used_indexes.add(index)
        selected.append(items[index])

    return sorted(selected, key=lambda item: item["session_number"])


def recovery_session_index(sessions):
    if not sessions:
        return None

    last_index = len(sessions) - 1
    last = sessions[last_index]
    full_hours = last.get("session_hours", 0)

    if full_hours and last["hours"] >= full_hours - 1:
        return last_index

    for index in range(last_index - 1, -1, -1):
        if sessions[index]["hours"] == full_hours:
            return index

    return last_index


def previous_session_index(sessions, current_index):
    if current_index is None:
        return None

    for index in range(current_index - 1, -1, -1):
        if sessions[index]["hours"] >= 3:
            return index

    return current_index - 1 if current_index > 0 else None


def duration_text(event_type, session):
    session_hours = session.get("session_hours", 0)

    if event_type == "activity":
        if not session.get("hours"):
            return ""

        return f"{3 if session['hours'] == 3 else 4} horas"

    if not session.get("session_hours") and not session.get("hours"):
        return ""

    return f"{session_hours or session['hours']} horas"


def evaluation_date_text(session):
    if not session.get("date"):
        return ""

    session_number = session.get("module_session_number", session.get("session_number"))
    return f"{format_date(session['date'])}\n(Sesión {session_number})"


def build_evaluation_events(module, schedule):
    sessions = module_sessions(module, schedule)

    if not sessions:
        return {}

    recovery_index = recovery_session_index(sessions)
    final_index = previous_session_index(sessions, recovery_index)

    activity_count = evaluable_activity_count(module_hours(module))
    blocked_indexes = {index for index in (final_index, recovery_index) if index is not None}

    eligible_activity_sessions = [
        session
        for index, session in enumerate(sessions)
        if index not in blocked_indexes
        and index > 0
        and session["hours"] >= 3
        and (final_index is None or index < final_index)
    ]
    selected_activity_sessions = select_evenly(eligible_activity_sessions, activity_count)

    events_by_block = {}

    for activity_number, session in enumerate(selected_activity_sessions, start=1):
        events_by_block.setdefault(session["block_code"], []).append({
            "type": "activity",
            "label": f"E{activity_number}: Actividad Evaluable",
            "activity_number": activity_number,
            "session": session,
        })

    if final_index is not None:
        session = sessions[final_index]
        events_by_block.setdefault(session["block_code"], []).append({
            "type": "final",
            "label": "Prueba final",
            "session": session,
        })

    if recovery_index is not None:
        session = sessions[recovery_index]
        events_by_block.setdefault(session["block_code"], []).append({
            "type": "recovery",
            "label": "Prueba de recuperación",
            "session": session,
        })

    for events in events_by_block.values():
        events.sort(key=lambda event: event["session"]["session_number"])

    return events_by_block


def activity_numbers_by_block(module, schedule):
    result = {}

    for block_code_value, events in build_evaluation_events(module, schedule).items():
        activity_numbers = {
            event["activity_number"]
            for event in events
            if event["type"] == "activity"
        }

        if activity_numbers:
            result[block_code_value] = activity_numbers

    return result
