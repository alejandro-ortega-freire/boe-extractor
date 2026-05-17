import fitz
from source.cleaning import clean_line, is_boe_noise


def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)


def get_words(page):
    words = []

    for w in page.get_text("words"):
        x0, y0, x1, y1, word, *_ = w

        if is_boe_noise(word):
            continue

        words.append({
            "text": word,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "cx": (x0 + x1) / 2,
            "cy": (y0 + y1) / 2,
        })

    return words


def words_to_lines(words, y_tolerance=3):
    words = sorted(words, key=lambda w: (w["y0"], w["x0"]))
    lines = []

    for word in words:
        placed = False

        for line in lines:
            if abs(line["y"] - word["y0"]) <= y_tolerance:
                line["words"].append(word)
                placed = True
                break

        if not placed:
            lines.append({
                "y": word["y0"],
                "words": [word]
            })

    result = []

    for line in lines:
        line_words = sorted(line["words"], key=lambda w: w["x0"])
        text = clean_line(" ".join(w["text"] for w in line_words))

        if text and not is_boe_noise(text):
            result.append({
                "text": text,
                "words": line_words,
                "x0": min(w["x0"] for w in line_words),
                "x1": max(w["x1"] for w in line_words),
                "y0": min(w["y0"] for w in line_words),
                "y1": max(w["y1"] for w in line_words),
            })

    return sorted(result, key=lambda l: (l["y0"], l["x0"]))


def get_drawn_table_lines(page):
    horizontal = []
    vertical = []

    for drawing in page.get_drawings():
        for item in drawing.get("items", []):
            if item[0] != "l":
                continue

            p1 = item[1]
            p2 = item[2]

            if abs(p1.y - p2.y) < 1:
                x0 = min(p1.x, p2.x)
                x1 = max(p1.x, p2.x)
                y = p1.y

                if x1 - x0 > 40:
                    horizontal.append({
                        "x0": x0,
                        "x1": x1,
                        "y": y,
                    })

            elif abs(p1.x - p2.x) < 1:
                x = p1.x
                y0 = min(p1.y, p2.y)
                y1 = max(p1.y, p2.y)

                if y1 - y0 > 10:
                    vertical.append({
                        "x": x,
                        "y0": y0,
                        "y1": y1,
                    })

    return horizontal, vertical


def unique_sorted(values, tolerance=2):
    result = []

    for value in sorted(values):
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)

    return result


def overlap_amount(a0, a1, b0, b1):
    return max(0, min(a1, b1) - max(a0, b0))


def overlap_ratio(a0, a1, b0, b1):
    overlap = overlap_amount(a0, a1, b0, b1)
    base = min(a1 - a0, b1 - b0)

    if base <= 0:
        return 0

    return overlap / base


def text_lines_in_box(page, x0, y0, x1, y1):
    selected = []

    for w in get_words(page):
        if x0 <= w["cx"] <= x1 and y0 <= w["cy"] <= y1:
            selected.append(w)

    lines = words_to_lines(selected)
    return [l["text"] for l in lines]


def text_in_box(page, x0, y0, x1, y1):
    return clean_line(" ".join(text_lines_in_box(page, x0, y0, x1, y1)))


def find_pages_with_requirements(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []

    for index, page in enumerate(doc):
        text = page.get_text("text")

        if "REQUISITOS MÍNIMOS DE ESPACIOS" in text or "Espacio Formativo" in text:
            pages.append(index)

    return pages


def get_geometric_table_candidates(page):
    horizontal, vertical = get_drawn_table_lines(page)
    candidates = []
    seen = set()

    if len(horizontal) < 2 or not vertical:
        return candidates

    for seed in vertical:
        group_verticals = []

        for v in vertical:
            if overlap_ratio(seed["y0"], seed["y1"], v["y0"], v["y1"]) >= 0.65:
                group_verticals.append(v)

        if not group_verticals:
            continue

        y0 = min(v["y0"] for v in group_verticals)
        y1 = max(v["y1"] for v in group_verticals)

        row_lines = [
            h for h in horizontal
            if y0 - 2 <= h["y"] <= y1 + 2
        ]

        if len(row_lines) < 2:
            continue

        table_x0 = min(h["x0"] for h in row_lines)
        table_x1 = max(h["x1"] for h in row_lines)

        xs = [
            v["x"] for v in group_verticals
            if table_x0 - 3 <= v["x"] <= table_x1 + 3
        ]

        col_xs = unique_sorted([table_x0] + xs + [table_x1])
        row_ys = unique_sorted([h["y"] for h in row_lines])

        if len(col_xs) < 3 or len(row_ys) < 2:
            continue

        key = (
            round(table_x0),
            round(y0),
            round(table_x1),
            round(y1),
            tuple(round(x) for x in col_xs),
            tuple(round(y) for y in row_ys),
        )

        if key in seen:
            continue

        seen.add(key)

        candidates.append({
            "x0": table_x0,
            "x1": table_x1,
            "y0": min(row_ys),
            "y1": max(row_ys),
            "col_xs": col_xs,
            "row_ys": row_ys,
        })

    return sorted(candidates, key=lambda c: (c["y0"], c["x0"]))


def get_table_header_text(page, candidate):
    row_ys = candidate["row_ys"]

    if len(row_ys) < 2:
        return ""

    return text_in_box(
        page,
        candidate["x0"],
        row_ys[0],
        candidate["x1"],
        row_ys[1]
    ).lower()


def merge_lowercase_continuations(lines):
    merged = []

    for line in lines:
        line = clean_line(line)

        if not line:
            continue

        if merged and line[0].islower():
            merged[-1] = clean_line(merged[-1] + " " + line)
        else:
            merged.append(line)

    return merged


def split_names_to_count(name_lines, expected_count):
    lines = merge_lowercase_continuations(name_lines)

    if expected_count <= 0:
        return lines

    if len(lines) == expected_count:
        return lines

    if len(lines) < expected_count:
        return lines

    fixed = []

    for i in range(expected_count - 1):
        fixed.append(lines[i])

    fixed.append(clean_line(" ".join(lines[expected_count - 1:])))

    return fixed


def get_next_table_y(candidates, current_candidate):
    next_tables = [
        candidate["y0"]
        for candidate in candidates
        if candidate["y0"] > current_candidate["y0"] + 5
    ]

    if not next_tables:
        return None

    return min(next_tables)