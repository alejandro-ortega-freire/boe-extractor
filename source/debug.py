import os

from source.config import DEBUG_FOLDER, DEBUG_GEOMETRY
from source.geometry import (
    find_pages_with_requirements,
    get_geometric_table_candidates,
    get_table_header_text,
    text_in_box,
)


def dump_geometry_debug(pdf_path):
    if not DEBUG_GEOMETRY:
        return

    os.makedirs(DEBUG_FOLDER, exist_ok=True)

    import fitz
    doc = fitz.open(pdf_path)

    base = os.path.splitext(os.path.basename(pdf_path))[0]
    debug_path = os.path.join(DEBUG_FOLDER, f"{base}_geometry.txt")

    with open(debug_path, "w", encoding="utf-8") as f:
        for page_index in find_pages_with_requirements(pdf_path):
            page = doc[page_index]
            candidates = get_geometric_table_candidates(page)

            f.write(f"\n=== Página {page_index + 1} ===\n")

            for idx, candidate in enumerate(candidates, start=1):
                header = get_table_header_text(page, candidate)

                f.write(f"\n--- Tabla geométrica {idx} ---\n")
                f.write(f"Header: {header}\n")
                f.write(f"X: {candidate['col_xs']}\n")
                f.write(f"Y: {candidate['row_ys']}\n")

                col_xs = candidate["col_xs"]
                row_ys = candidate["row_ys"]

                for r in range(len(row_ys) - 1):
                    cells = []

                    for c in range(len(col_xs) - 1):
                        cell = text_in_box(
                            page,
                            col_xs[c],
                            row_ys[r],
                            col_xs[c + 1],
                            row_ys[r + 1]
                        )
                        cells.append(cell)

                    f.write(" | ".join(cells))
                    f.write("\n")