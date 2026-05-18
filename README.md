# BOE Extractor

Aplicación en Python para extraer información de Certificados de Profesionalidad del BOE y generar automáticamente documentos Word estructurados.

Autor: Alejandro Ortega Freire

## Funcionalidades

- Extracción automática de:
  - Datos básicos del certificado
  - Módulos formativos
  - Unidades formativas
  - Duración total
  - Espacios formativos
  - Equipamiento
  - Capacidades y criterios de evaluación

- Generación automática de documentos `.docx`

- Extracción geométrica avanzada mediante coordenadas PDF:
  - Tablas
  - Equipamiento
  - Espacios formativos
  - Criterios y subcriterios

## Tecnologías

- Python
- PyMuPDF (`fitz`)
- python-docx

## Estructura del proyecto

```text
boe-extractor/
├─ source/
├─ input/
├─ output/
├─ debug_tables/
├─ main.py
├─ requirements.txt
├─ README.md
└─ .gitignore
