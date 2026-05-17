import re
import fitz

from source.cleaning import clean_line, dedupe_list, clean_dot_leaders
from source.geometry import (
    find_pages_with_requirements,
    get_geometric_table_candidates,
    get_table_header_text,
    text_lines_in_box,
    split_names_to_count,
    get_next_table_y,
)


def clean_space_name(name):
    name = clean_line(name)
    name = clean_dot_leaders(name)
    return name


def extract_spaces_geometric(pdf_path):
    doc = fitz.open(pdf_path)
    spaces = []

    for page_index in find_pages_with_requirements(pdf_path):
        page = doc[page_index]
        candidates = get_geometric_table_candidates(page)

        previous_was_surface_header = False

        for candidate in candidates:
            header = get_table_header_text(page, candidate)

            col_xs = candidate["col_xs"]
            row_ys = candidate["row_ys"]

            if len(col_xs) < 4:
                previous_was_surface_header = (
                    "espacio formativo" in header and "superficie" in header
                )
                continue

            first_col_x0 = col_xs[0]
            first_col_x1 = col_xs[1]

            is_surface_header = (
                "espacio formativo" in header and "superficie" in header
            )

            # Caso normal: cabecera y datos dentro del mismo bloque geométrico.
            if is_surface_header:
                data_y0 = row_ys[1]

                if len(row_ys) <= 2:
                    next_y = get_next_table_y(candidates, candidate)
                    data_y1 = next_y - 3 if next_y else candidate["y1"]
                else:
                    data_y1 = row_ys[-1]

            # Caso partido: la cabecera está en el bloque anterior y este bloque solo tiene datos.
            elif previous_was_surface_header:
                data_y0 = row_ys[0]
                data_y1 = row_ys[-1]

            else:
                previous_was_surface_header = False
                continue

            if data_y1 <= data_y0:
                previous_was_surface_header = is_surface_header
                continue

            left_lines = text_lines_in_box(
                page,
                first_col_x0,
                data_y0,
                first_col_x1,
                data_y1
            )

            number_columns = []

            for col_index in range(1, len(col_xs) - 1):
                col_text_lines = text_lines_in_box(
                    page,
                    col_xs[col_index],
                    data_y0,
                    col_xs[col_index + 1],
                    data_y1
                )

                nums = []

                for line in col_text_lines:
                    nums.extend(re.findall(r"\b\d+(?:,\d+)?\b", line))

                if nums:
                    number_columns.append(nums)

            if len(number_columns) < 2:
                previous_was_surface_header = is_surface_header
                continue

            expected_count = min(len(number_columns[0]), len(number_columns[1]))
            names = split_names_to_count(left_lines, expected_count)

            if len(names) != expected_count:
                previous_was_surface_header = is_surface_header
                continue

            for i, name in enumerate(names):
                name = clean_space_name(name)
                n1 = number_columns[0][i]
                n2 = number_columns[1][i]

                if name and not name.lower().startswith("alumnos"):
                    spaces.append(
                        f"{name} de {n1} m2 (para 15 alumnos) o de {n2} m2 (para 25 alumnos)"
                    )

            previous_was_surface_header = is_surface_header

    return dedupe_list(spaces)