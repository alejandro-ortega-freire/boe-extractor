from functools import lru_cache
from pathlib import Path

from source.pipeline import build_payload


ROOT = Path(__file__).resolve().parents[1]
MAMD0309_PDF = ROOT / "input" / "MAMD0309.pdf"


def require_pdf(test_case, path):
    if not path.exists():
        test_case.skipTest(f"No existe el PDF de prueba: {path}")


@lru_cache(maxsize=4)
def payload_for(pdf_name):
    return build_payload(str(ROOT / "input" / pdf_name))


def find_training_module(payload, code):
    for module in payload.training_modules:
        if module.code == code:
            return module

    raise AssertionError(f"No se encontró el módulo {code}")


def find_uf(module, code):
    for uf in module.ufs:
        if uf.code == code:
            return uf

    raise AssertionError(f"No se encontró la UF {code} en {module.code}")


def flatten_bullets(bullets):
    result = []

    for bullet in bullets:
        result.append(bullet.text)
        result.extend(flatten_bullets(bullet.children))

    return result
