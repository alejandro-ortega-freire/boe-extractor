import os

from source.config import INPUT_FOLDER, OUTPUT_FOLDER
from source.cleaning import clean_text
from source.geometry import extract_text
from source.basic_data import extract_basic_data
from source.modules import extract_modules, calculate_certificate_duration
from source.training_section import extract_training_modules
from source.extract_criteria import extract_criteria_geometric, merge_geometric_criteria
from source.extract_contents import extract_contents_geometric, merge_geometric_contents
from source.extract_spaces import extract_spaces_geometric
from source.extract_equipment import extract_equipment_groups_geometric
from source.fallbacks import fallback_spaces_from_text, fallback_equipment_from_text
from source.debug import dump_geometry_debug
from source.word_writer import create_docx


if __name__ == "__main__":
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pdf_files = [
        file for file in os.listdir(INPUT_FOLDER)
        if file.lower().endswith(".pdf")
    ]

    if not pdf_files:
        print("No hay PDFs en la carpeta input.")
    else:
        for pdf_file in pdf_files:
            print(f"Procesando: {pdf_file}")

            pdf_path = os.path.join(INPUT_FOLDER, pdf_file)
            base_name = os.path.splitext(pdf_file)[0]
            output_path = os.path.join(OUTPUT_FOLDER, f"resultado_{base_name}.docx")

            raw_text = extract_text(pdf_path)
            text = clean_text(raw_text)

            data = extract_basic_data(text)
            modules = extract_modules(text)
            duration_text = calculate_certificate_duration(modules)

            training_modules = extract_training_modules(text, modules)

            criteria_by_module = extract_criteria_geometric(pdf_path)
            training_modules = merge_geometric_criteria(
                training_modules,
                criteria_by_module
            )

            contents_by_module = extract_contents_geometric(pdf_path)
            training_modules = merge_geometric_contents(
                training_modules,
                contents_by_module
            )

            dump_geometry_debug(pdf_path)

            spaces = extract_spaces_geometric(pdf_path)
            equipment_groups = extract_equipment_groups_geometric(pdf_path)

            if not spaces:
                spaces = fallback_spaces_from_text(text)

            if not equipment_groups:
                equipment_groups = fallback_equipment_from_text(text)

            create_docx(
                data,
                modules,
                spaces,
                equipment_groups,
                duration_text,
                training_modules,
                output_path
            )

            print(f"Generado: {output_path}")
