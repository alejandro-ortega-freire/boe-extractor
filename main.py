import os
import sys

from source.config import INPUT_FOLDER, OUTPUT_FOLDER
from source.pipeline import process_pdf
from source.schedule import prompt_schedule_config


def set_runtime_working_directory():
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))


if __name__ == "__main__":
    set_runtime_working_directory()
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pdf_files = [
        file for file in os.listdir(INPUT_FOLDER)
        if file.lower().endswith(".pdf")
    ]

    if not pdf_files:
        print("No hay PDFs en la carpeta input.")
    else:
        schedule_config = prompt_schedule_config()

        for pdf_file in pdf_files:
            print(f"Procesando: {pdf_file}")

            pdf_path = os.path.join(INPUT_FOLDER, pdf_file)
            generated_files = process_pdf(pdf_path, schedule_config)

            for output_path in generated_files:
                print(f"Generado: {output_path}")
