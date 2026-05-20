from datetime import date, datetime, timedelta
import re

from source.settings import (
    DEFAULT_SESSION_HOURS,
    DEFAULT_TEACHER_NAME,
    MAX_SESSION_HOURS,
    MIN_SESSION_HOURS,
)


def parse_hours(text):
    found = re.findall(r"\((\d+)\s*horas?\)", text or "", flags=re.IGNORECASE)
    return int(found[-1]) if found else 0


def code_from_text(text):
    match = re.search(r"\b(?:MF\d{4}_\d|MP\d{4}|UF\d{4})\b", text or "")
    return match.group(0) if match else ""


def easter_sunday(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def holidays_for_year(year):
    easter = easter_sunday(year)
    holidays = {
        date(year, 1, 1): "Año Nuevo",
        date(year, 1, 6): "Epifanía del Señor",
        easter - timedelta(days=3): "Jueves Santo",
        easter - timedelta(days=2): "Viernes Santo",
        date(year, 5, 1): "Fiesta del Trabajo",
        date(year, 5, 30): "Día de Canarias",
        date(year, 8, 15): "Asunción de la Virgen",
        date(year, 10, 12): "Fiesta Nacional de España",
        date(year, 11, 1): "Todos los Santos",
        date(year, 12, 6): "Día de la Constitución Española",
        date(year, 12, 8): "Inmaculada Concepción",
        date(year, 12, 25): "Natividad del Señor",
        date(year, 2, 2): "Nuestra Señora de la Candelaria (Tenerife)",
    }
    return holidays


def holidays_between(start_date, end_date):
    holidays = {}

    for year in range(start_date.year, end_date.year + 1):
        holidays.update(holidays_for_year(year))

    return {
        day: name
        for day, name in holidays.items()
        if start_date <= day <= end_date
    }


def is_working_day(day):
    if day.weekday() >= 5:
        return False

    return day not in holidays_for_year(day.year)


def next_working_day(day):
    while not is_working_day(day):
        day += timedelta(days=1)

    return day


def default_start_date(today=None):
    today = today or date.today()
    candidate = today + timedelta(days=1)

    while candidate.weekday() != 0:
        candidate += timedelta(days=1)

    return next_working_day(candidate)


def parse_date(value):
    value = (value or "").strip()

    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue

    return None


def prompt_session_hours():
    prompt = (
        f"Tamaño de la sesión en horas "
        f"({MIN_SESSION_HOURS}-{MAX_SESSION_HOURS}, defecto {DEFAULT_SESSION_HOURS}): "
    )
    value = input(prompt).strip()

    if not value:
        return DEFAULT_SESSION_HOURS

    try:
        hours = int(value)
    except ValueError:
        print(f"Valor no válido. Se usará {DEFAULT_SESSION_HOURS} horas.")
        return DEFAULT_SESSION_HOURS

    if MIN_SESSION_HOURS <= hours <= MAX_SESSION_HOURS:
        return hours

    print(f"Valor fuera de rango. Se usará {DEFAULT_SESSION_HOURS} horas.")
    return DEFAULT_SESSION_HOURS


def prompt_teacher_name():
    value = input(f"Nombre del docente (defecto {DEFAULT_TEACHER_NAME}): ").strip()
    return value or DEFAULT_TEACHER_NAME


def prompt_start_date():
    default = default_start_date()
    value = input(
        f"Fecha de inicio del certificado "
        f"(dd/mm/aaaa, defecto {format_date(default)}): "
    ).strip()

    if not value:
        return default

    parsed = parse_date(value)

    if parsed is None:
        print(f"Fecha no válida. Se usará {format_date(default)}.")
        return default

    if not is_working_day(parsed):
        adjusted = next_working_day(parsed)
        print(
            f"La fecha indicada no es lectiva. "
            f"Se usará {format_date(adjusted)}."
        )
        return adjusted

    return parsed


def prompt_copy_subcriteria():
    value = input("¿Copiar subcriterios en el Anexo IV? (y/n, defecto n): ").strip().lower()
    return value in ("y", "yes")


def prompt_schedule_config():
    return {
        "teacher_name": prompt_teacher_name(),
        "session_hours": prompt_session_hours(),
        "start_date": prompt_start_date(),
        "copy_subcriteria": prompt_copy_subcriteria(),
    }


def format_date(day, note=None):
    text = day.strftime("%d/%m/%Y")

    if note:
        text += f" ({note})"

    return text


def format_date_range(start_date, end_date, start_note=None, end_note=None):
    return f"{format_date(start_date, start_note)} - {format_date(end_date, end_note)}"


def iter_scheduled_items(modules):
    for module in modules:
        module_text = module.text
        module_code = code_from_text(module_text)
        ufs = module.ufs

        if module_code.startswith("MP"):
            yield module_code, parse_hours(module_text)
            continue

        if not ufs:
            yield module_code, parse_hours(module_text)
            continue

        for uf in ufs:
            yield code_from_text(uf), parse_hours(uf)


def calculate_schedule(modules, session_hours, start_date):
    """Distribute module/UF hours over working days and carry partial sessions forward."""
    current_date = next_working_day(start_date)
    used_hours = 0
    dates_by_code = {}
    first_date = current_date

    for code, hours in iter_scheduled_items(modules):
        if not code or hours <= 0:
            continue

        start = current_date
        start_note = session_hours - used_hours if used_hours else None
        remaining = hours
        end = current_date
        end_note = None

        while remaining > 0:
            available = session_hours - used_hours
            consumed = min(remaining, available)
            remaining -= consumed
            used_hours += consumed
            end = current_date

            if remaining == 0:
                if used_hours < session_hours:
                    end_note = consumed
                else:
                    used_hours = 0
                    current_date = next_working_day(current_date + timedelta(days=1))
                break

            used_hours = 0
            current_date = next_working_day(current_date + timedelta(days=1))

        dates_by_code[code] = {
            "start": start,
            "end": end,
            "start_note": start_note,
            "end_note": end_note,
            "text": format_date_range(start, end, start_note, end_note),
        }

    last_date = max((item["end"] for item in dates_by_code.values()), default=first_date)
    considered_holidays = holidays_between(first_date, last_date)

    return {
        "dates_by_code": dates_by_code,
        "start_date": first_date,
        "end_date": last_date,
        "session_hours": session_hours,
        "considered_holidays": considered_holidays,
    }


def format_holiday_note(schedule):
    holidays = schedule.get("considered_holidays", {})

    if not holidays:
        return "Festivos considerados: ninguno dentro del periodo planificado."

    parts = [
        f"{format_date(day)} ({name})"
        for day, name in sorted(holidays.items())
    ]
    return "Festivos considerados en la planificación: " + "; ".join(parts) + "."
