import os

from source.__about__ import __author__


ACTION_CODE = "24-38/001234"
DEFAULT_TEACHER_NAME = "Docente"

PLACEHOLDER_DATES = "FECHAS PENDIENTES"
PLACEHOLDER_CENTER = "Alejandro2000"
PLACEHOLDER_ADDRESS = "C/ Falsa 123, 38320 Santa Cruz de Tenerife"
PLACEHOLDER_LOCALITY = "Reino de la Piruleta"
PROVINCE = "Santa Cruz de Tenerife"

DEFAULT_SESSION_HOURS = 6
MIN_SESSION_HOURS = 1
MAX_SESSION_HOURS = 8
DEFAULT_STUDENT_COUNT = 16
MIN_STUDENT_COUNT = 1
MAX_STUDENT_COUNT = 100

LOGO_PATH = os.path.join("assets", "boe_extractor_logo.png")
CUSTOM_HOLIDAYS_FILE = "festivos.xlsx"
DEFAULT_AUTHOR = __author__
