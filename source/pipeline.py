import os

from source.anexo_iv_writer import build_module_filename, create_anexo_iv_docx
from source.anexo_v_writer import build_anexo_v_filename, create_anexo_v_docx
from source.anexo_vi_writer import create_anexo_vi_docx
from source.anexo_vii_writer import create_anexo_vii_docx
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
from source.models import DocumentPayload
from source.normalization import normalize_document_payload
from source.schedule import calculate_schedule
from source.training_section import extract_training_modules
from source.docx_utils import add_header_footer
from source.word_writer import create_anexo_iii_docx, create_info_docx


def safe_path_name(value, fallback):
    text = (value or fallback or "").strip()
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in text)
    safe = safe.strip("_")
    return safe or fallback


def certificate_output_paths(output_folder, certificate_code):
    certificate_folder = os.path.join(output_folder, certificate_code)
    folders = {
        "certificate": certificate_folder,
        "anexo_iii": os.path.join(certificate_folder, "Anexo III"),
        "anexo_iv": os.path.join(certificate_folder, "Anexos IV"),
        "anexo_v": os.path.join(certificate_folder, "Anexos V"),
        "anexo_vi": os.path.join(certificate_folder, "Anexo VI"),
        "anexo_vii": os.path.join(certificate_folder, "Anexo VII"),
    }
    files = {
        "info": os.path.join(certificate_folder, f"info_{certificate_code}.docx"),
        "anexo_iii": os.path.join(folders["anexo_iii"], f"anexoIII_{certificate_code}.docx"),
        "anexo_vi": os.path.join(folders["anexo_vi"], f"anexoVI_{certificate_code}.docx"),
        "anexo_vii": os.path.join(folders["anexo_vii"], f"anexoVII_{certificate_code}.docx"),
    }

    return {"folders": folders, "files": files}


def ensure_output_folders(paths):
    for folder in paths["folders"].values():
        os.makedirs(folder, exist_ok=True)


def module_output_paths(paths, module_code, certificate_code):
    return {
        "anexo_iv": os.path.join(
            paths["folders"]["anexo_iv"],
            build_module_filename(module_code, certificate_code),
        ),
        "anexo_v": os.path.join(
            paths["folders"]["anexo_v"],
            build_anexo_v_filename(module_code, certificate_code),
        ),
    }


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

    normalized_payload = normalize_document_payload(
        data,
        modules,
        spaces,
        equipment_groups,
        duration_text,
        training_modules
    )
    return DocumentPayload.from_dict(normalized_payload)


def process_pdf(pdf_path, config):
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    payload = build_payload(pdf_path)
    training_center = config.get("training_center")
    schedule = calculate_schedule(
        payload.modules,
        config["session_hours"],
        config["start_date"],
        config.get("custom_holidays")
    )

    certificate_code = safe_path_name(payload.data.codigo, base_name)
    paths = certificate_output_paths(OUTPUT_FOLDER, certificate_code)
    ensure_output_folders(paths)

    create_info_docx(
        payload.data,
        payload.modules,
        payload.spaces,
        payload.equipment_groups,
        payload.duration_text,
        payload.training_modules,
        paths["files"]["info"],
        config["teacher_name"]
    )

    create_anexo_iii_docx(
        payload.data,
        payload.modules,
        payload.duration_text,
        paths["files"]["anexo_iii"],
        schedule,
        config["teacher_name"],
        training_center
    )

    create_anexo_vi_docx(
        payload.data,
        payload.modules,
        payload.duration_text,
        paths["files"]["anexo_vi"],
        schedule,
        config["teacher_name"],
        training_center
    )

    create_anexo_vii_docx(
        payload.data,
        payload.modules,
        payload.duration_text,
        paths["files"]["anexo_vii"],
        schedule,
        config["teacher_name"],
        training_center,
        config.get("student_count")
    )

    generated_files = [
        paths["files"]["info"],
        paths["files"]["anexo_iii"],
        paths["files"]["anexo_vi"],
        paths["files"]["anexo_vii"],
    ]

    for training_module in payload.training_modules:
        module_code = safe_path_name(
            training_module.identifier.split(":", 1)[0],
            "MF"
        )
        module_paths = module_output_paths(paths, module_code, certificate_code)

        create_anexo_iv_docx(
            payload.data,
            training_module,
            payload.duration_text,
            module_paths["anexo_iv"],
            schedule,
            add_header_footer,
            config["copy_subcriteria"],
            payload.spaces,
            payload.equipment_groups,
            config["teacher_name"],
            training_center
        )

        generated_files.append(module_paths["anexo_iv"])

        create_anexo_v_docx(
            payload.data,
            training_module,
            payload.duration_text,
            module_paths["anexo_v"],
            schedule,
            payload.spaces,
            add_header_footer,
            config["teacher_name"],
            training_center
        )

        generated_files.append(module_paths["anexo_v"])

    return generated_files
