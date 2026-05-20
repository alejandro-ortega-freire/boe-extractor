import os

from source.anexo_iv_writer import build_module_filename, create_anexo_iv_docx
from source.basic_data import extract_basic_data
from source.cleaning import clean_text
from source.config import OUTPUT_FOLDER
from source.debug import dump_geometry_debug
from source.extract_contents import extract_contents_geometric, merge_geometric_contents
from source.extract_criteria import extract_criteria_geometric, merge_geometric_criteria
from source.extract_equipment import extract_equipment_groups_geometric
from source.extract_spaces import extract_spaces_geometric
from source.fallbacks import fallback_equipment_from_text, fallback_spaces_from_text
from source.geometry import extract_text
from source.modules import calculate_certificate_duration, extract_modules
from source.normalization import normalize_document_payload
from source.schedule import calculate_schedule
from source.training_section import extract_training_modules
from source.word_writer import add_header_footer, create_anexo_iii_docx, create_info_docx


def safe_path_name(value, fallback):
    text = (value or fallback or "").strip()
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in text)
    safe = safe.strip("_")
    return safe or fallback


def build_payload(pdf_path):
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

    return normalize_document_payload(
        data,
        modules,
        spaces,
        equipment_groups,
        duration_text,
        training_modules
    )


def process_pdf(pdf_path, config):
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    payload = build_payload(pdf_path)
    schedule = calculate_schedule(
        payload["modules"],
        config["session_hours"],
        config["start_date"]
    )

    certificate_code = safe_path_name(payload["data"].get("codigo"), base_name)
    certificate_output_folder = os.path.join(OUTPUT_FOLDER, certificate_code)
    os.makedirs(certificate_output_folder, exist_ok=True)

    info_output_path = os.path.join(
        certificate_output_folder,
        f"info_{certificate_code}.docx"
    )
    anexo_output_path = os.path.join(
        certificate_output_folder,
        f"anexoIII_{certificate_code}.docx"
    )

    create_info_docx(
        payload["data"],
        payload["modules"],
        payload["spaces"],
        payload["equipment_groups"],
        payload["duration_text"],
        payload["training_modules"],
        info_output_path,
        config["teacher_name"]
    )

    create_anexo_iii_docx(
        payload["data"],
        payload["modules"],
        payload["duration_text"],
        anexo_output_path,
        schedule,
        config["teacher_name"]
    )

    generated_files = [info_output_path, anexo_output_path]

    for training_module in payload["training_modules"]:
        module_code = safe_path_name(
            training_module.get("identifier", "").split(":", 1)[0],
            "MF"
        )
        anexo_iv_output_path = os.path.join(
            certificate_output_folder,
            build_module_filename(module_code, certificate_code)
        )

        create_anexo_iv_docx(
            payload["data"],
            training_module,
            payload["duration_text"],
            anexo_iv_output_path,
            schedule,
            add_header_footer,
            config["copy_subcriteria"],
            payload["spaces"],
            payload["equipment_groups"],
            config["teacher_name"]
        )

        generated_files.append(anexo_iv_output_path)

    return generated_files
