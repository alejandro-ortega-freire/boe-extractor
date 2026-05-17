import re
import fitz

from source.cleaning import clean_line, dedupe_list, dedupe_groups
from source.geometry import (
    find_pages_with_requirements,
    get_geometric_table_candidates,
    get_table_header_text,
    text_lines_in_box,
    merge_lowercase_continuations,
    get_next_table_y,
)


def normalize_equipment_items_from_lines(lines):
    items = []

    for line in lines:
        line = clean_line(line)

        if not line:
            continue

        starts_new = (
            line.startswith("-") or
            (line and line[0].isupper())
        )

        line = re.sub(r"^-+\s*", "", line).strip()

        if not line:
            continue

        if starts_new or not items:
            items.append(line)
        else:
            items[-1] += " " + line

    return dedupe_list(items)


def extract_equipment_groups_geometric(pdf_path):
    doc = fitz.open(pdf_path)
    groups = []

    for page_index in find_pages_with_requirements(pdf_path):
        page = doc[page_index]
        candidates = get_geometric_table_candidates(page)

        for candidate in candidates:
            header = get_table_header_text(page, candidate)

            if "espacio formativo" not in header:
                continue

            if "equipamiento" not in header:
                continue

            col_xs = candidate["col_xs"]
            row_ys = candidate["row_ys"]

            if len(col_xs) < 3:
                continue

            left_x0 = col_xs[0]
            split_x = col_xs[1]
            right_x1 = col_xs[-1]

            if len(row_ys) <= 2:
                next_y = get_next_table_y(candidates, candidate)
                content_y0 = row_ys[1]
                content_y1 = next_y - 3 if next_y else candidate["y1"]

                group_lines = text_lines_in_box(
                    page,
                    left_x0,
                    content_y0,
                    split_x,
                    content_y1
                )

                item_lines = text_lines_in_box(
                    page,
                    split_x,
                    content_y0,
                    right_x1,
                    content_y1
                )

                group_name = clean_line(" ".join(merge_lowercase_continuations(group_lines)))
                items = normalize_equipment_items_from_lines(item_lines)

                if group_name and items:
                    groups.append({
                        "name": group_name,
                        "items": items
                    })

                continue

            for i in range(1, len(row_ys) - 1):
                y0 = row_ys[i]
                y1 = row_ys[i + 1]

                group_lines = text_lines_in_box(
                    page,
                    left_x0,
                    y0,
                    split_x,
                    y1
                )

                item_lines = text_lines_in_box(
                    page,
                    split_x,
                    y0,
                    right_x1,
                    y1
                )

                group_name = clean_line(" ".join(merge_lowercase_continuations(group_lines)))
                items = normalize_equipment_items_from_lines(item_lines)

                if not group_name or not items:
                    continue

                if "espacio formativo" in group_name.lower():
                    continue

                if "equipamiento" in group_name.lower():
                    continue

                groups.append({
                    "name": group_name,
                    "items": items
                })

    return dedupe_groups(groups)