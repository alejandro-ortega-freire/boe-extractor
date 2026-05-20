# Arquitectura BOEExtractor

## Objetivo del proyecto

BOEExtractor procesa PDFs del BOE de certificados profesionales y genera documentos Word organizados para revisión y planificación didáctica.

Por cada PDF de entrada se crea una carpeta con el código del certificado y, dentro, estos documentos:

- `info_<codigo_certificado>.docx`: información completa extraída del BOE.
- `anexoIII_<codigo_certificado>.docx`: planificación didáctica general del certificado.
- `anexoIV_<codigo_modulo>_<codigo_certificado>.docx`: programación didáctica por cada módulo formativo no práctico.

## Flujo Principal

El flujo general es:

```text
PDF -> extractores -> normalizer -> schedule -> writers DOCX
```

La entrada está en `input/` y la salida se escribe en `output/<codigo_certificado>/`.

El programa se ejecuta desde `main.py`, que:

1. Prepara el directorio de trabajo cuando se ejecuta como `.exe`.
2. Busca PDFs dentro de `input/`.
3. Pregunta configuración al usuario.
4. Llama a `process_pdf(pdf_path, config)` por cada PDF.

La lógica principal vive en `source/pipeline.py`.

## Pipeline

`source/pipeline.py` coordina el proceso completo.

Funciones principales:

- `build_payload(pdf_path)`: extrae datos del PDF y devuelve un `DocumentPayload`.
- `process_pdf(pdf_path, config)`: genera todos los documentos Word para un PDF.
- `safe_path_name(value, fallback)`: convierte códigos o nombres en rutas seguras.

`build_payload()` hace estas fases:

1. Extrae texto bruto con `geometry.extract_text()`.
2. Limpia el texto con `cleaning.clean_text()`.
3. Extrae datos básicos, módulos, duración, criterios, contenidos, espacios y equipamiento.
4. Fusiona extracción textual y geométrica.
5. Normaliza todo con `normalize_document_payload()`.
6. Convierte el resultado a dataclasses con `DocumentPayload.from_dict()`.

## Modelo De Datos

Los modelos principales están en `source/models.py`.

Los más importantes son:

- `DocumentPayload`: contenedor completo de datos de un certificado.
- `BasicData`: datos básicos del certificado.
- `ModuleSummary`: módulo del resumen inicial del certificado.
- `TrainingModule`: módulo formativo detallado.
- `TrainingUnit`: unidad formativa.
- `Criterion`: criterio principal `C1`, `C2`, etc.
- `Subcriterion`: subcriterio `CE1.1`, `CE1.2`, etc.
- `ContentItem`: contenido numerado oficial.
- `Bullet`: bullet de contenido, con hijos para niveles internos.
- `EquipmentGroup`: grupo de equipamiento.

Hay compatibilidad con diccionarios porque parte de los extractores todavía devuelven estructuras simples antes de la normalización.

## Extractores

Los extractores convierten el PDF en datos intermedios.

- `source/basic_data.py`: extrae código, nombre, familia profesional y nivel.
- `source/modules.py`: extrae la relación inicial de módulos y UFs.
- `source/training_section.py`: extrae la sección formativa detallada.
- `source/extract_criteria.py`: extrae capacidades y criterios de evaluación.
- `source/extract_contents.py`: extrae contenidos numerados y bullets.
- `source/extract_spaces.py`: extrae espacios formativos.
- `source/extract_equipment.py`: extrae equipamiento.
- `source/fallbacks.py`: aporta extracción alternativa si falla la ruta geométrica.
- `source/geometry.py`: utilidades de lectura geométrica del PDF.

La extracción geométrica es importante porque muchos BOE dependen de indentación visual para expresar listas, niveles de bullets y fronteras entre apartados.

## Normalización

La normalización está en:

- `source/cleaning.py`
- `source/normalization.py`

Su objetivo es que los writers reciban texto seguro y estructuras consistentes.

Responsabilidades típicas:

- Quitar caracteres incompatibles con XML/Word.
- Evitar espacios antes de puntuación.
- Corregir puntos decorativos residuales.
- Normalizar bullets textuales que no deben aparecer como caracteres.
- Convertir dicts a estructuras limpias antes de crear dataclasses.

`word_writer.py`, `anexo_iii_writer.py` y `anexo_iv_writer.py` también aplican defensas puntuales, pero la limpieza principal debería ocurrir antes de llegar al renderizado.

## Asignación De Contenidos

La asignación semántica del Anexo IV está en el paquete `source/content_assignment/`.

Archivos principales:

- `tokenizer.py`: tokenización, stopwords y normalización semántica.
- `constants.py`: pesos, familias semánticas y sinónimos.
- `signatures.py`: creación de firmas semánticas para criterios y contenidos.
- `scoring.py`: cálculo de puntuaciones de similitud.
- `splitting.py`: partición de contenidos amplios en subbloques.
- `balancing.py`: reequilibrado para evitar huecos y contenidos sin asignar.
- `rendering.py`: reconstrucción de contenidos asignados para el Word.
- `assigner.py`: función principal de asignación.

Reglas prioritarias:

- Ningún criterio debe quedar sin contenido si existe contenido oficial disponible.
- Ningún contenido oficial debe quedar sin asignar.
- No se deben mezclar contenidos entre módulos distintos.
- No se deben mezclar contenidos entre UFs distintas.
- Es preferible partir contenidos antes que duplicarlos.
- La duplicación solo debería aparecer como último recurso.
- Si una asignación es sugerida por heurística, puede marcarse visualmente como sugerencia.

Esta zona sigue siendo heurística. Está mejor estructurada, pero seguirá necesitando ajustes con más anexos verdad.

## Generación DOCX

La generación Word está repartida en writers y utilidades comunes.

Writers:

- `source/word_writer.py`: genera el documento `info_<codigo>.docx`.
- `source/anexo_iii_writer.py`: genera el Anexo III.
- `source/anexo_iv_writer.py`: genera los Anexos IV por módulo.

Utilidades:

- `source/docx_utils.py`: cabecera, pie, número de página, texto seguro y líneas horizontales.
- `source/table_styles.py`: sombreado, márgenes, anchos, bordes y alturas de filas.
- `source/docx_styles.py`: constantes visuales de Word.

Los writers deberían centrarse en qué documento crear. Los detalles repetidos de XML de Word deben vivir en helpers comunes.

## Configuración

La configuración está separada por intención:

- `source/config.py`: carpetas de entrada, salida y depuración.
- `source/settings.py`: textos fijos, placeholders, código de acción, docente por defecto y rutas de assets.
- `source/docx_styles.py`: colores, tamaños, anchos y medidas de Word.
- `source/__about__.py`: nombre de aplicación, versión y autoría.

Cuando el cambio sea estético o de texto fijo, primero conviene mirar `settings.py` y `docx_styles.py` antes de modificar writers.

## Planificación De Fechas

La planificación está en `source/schedule.py`.

Responsabilidades:

- Preguntar nombre del docente.
- Preguntar duración de sesión.
- Preguntar fecha de inicio.
- Calcular días lectivos.
- Saltar sábados, domingos y festivos considerados.
- Distribuir horas de módulos y UFs.
- Gestionar sesiones parciales.
- Formatear rangos de fechas.

El resultado se consume principalmente en Anexo III y Anexo IV.

## Tests

Los tests están en `tests/`.

Se ejecutan con:

```powershell
python -m unittest discover -s tests -v
```

Actualmente protegen casos como:

- Limpieza de texto incompatible con Word.
- Extracción de criterios.
- Extracción de contenidos.
- Caso MAMD0309.
- UF1186 con criterios y contenidos.
- Bullet falso `sectoriales.`.
- Módulos que arrastran `(120 horas)`.
- Asignación de contenidos sin celdas vacías.
- Comparación básica de Anexos IV contra documentos verdad cuando están disponibles.
- Planificación de sesiones y fechas.

`tests/fixtures/` queda reservado para documentar o añadir casos problemáticos futuros sin duplicar archivos pesados innecesariamente.

## Zonas Frágiles Conocidas

### PDFs Con Texto Partido

El PDF puede partir una frase visualmente y hacer que una línea parezca un bullet nuevo. Esto afecta especialmente a contenidos y subcriterios.

Ejemplo típico:

```text
Vaciado selectivo de revistas especializadas e información de novedades
sectoriales.
```

La palabra `sectoriales.` no debe convertirse en un sub-bullet.

### Fronteras Entre Módulos Y UFs

Si falla la detección de `MÓDULO FORMATIVO`, `UNIDAD FORMATIVA` o `MÓDULO DE PRÁCTICAS`, los datos pueden acabar en el bloque incorrecto.

Por eso `training_section.py`, `extract_criteria.py` y `extract_contents.py` deben tratar esas cabeceras como fronteras duras.

### Asignación Semántica

La asignación de contenidos a criterios no es una verdad matemática. Usa heurísticas basadas en tokens, verbos, familias técnicas, orden y partición de bloques.

Debe ajustarse con tests y anexos verdad, no con excepciones hardcodeadas para un único certificado.

### Word Y XML Interno

`python-docx` no expone todas las opciones necesarias. Algunas cosas, como bordes, sombreado, números de página y líneas horizontales, usan XML interno.

Estos detalles deben mantenerse encapsulados en `docx_utils.py` y `table_styles.py`.

### Compatibilidad Dicts / Dataclasses

El proyecto ya usa dataclasses para el dominio, pero algunos extractores siguen devolviendo dicts. Esto es aceptable mientras la normalización convierta la salida antes de los writers.

## Cómo Añadir Una Mejora

### Cambiar Textos Fijos O Placeholders

Mirar primero:

- `source/settings.py`

Ejemplos:

- Código de acción.
- Centro de formación.
- Dirección.
- Localidad.
- Provincia.
- Docente por defecto.

### Cambiar Estética De Word

Mirar primero:

- `source/docx_styles.py`
- `source/table_styles.py`
- `source/docx_utils.py`

Evitar tocar directamente XML en los writers salvo que sea una necesidad muy concreta.

### Corregir Extracción De Contenidos

Mirar:

- `source/extract_contents.py`
- `source/geometry.py`
- `tests/test_extract_contents.py`

Añadir primero un test con el caso roto si es posible.

### Corregir Extracción De Criterios

Mirar:

- `source/extract_criteria.py`
- `source/training_section.py`
- `tests/test_extract_criteria.py`
- `tests/test_training_section.py`

### Ajustar Asignación Semántica

Mirar:

- `source/content_assignment/scoring.py`
- `source/content_assignment/signatures.py`
- `source/content_assignment/splitting.py`
- `source/content_assignment/balancing.py`

Después ejecutar tests de asignación y, si procede, comparar contra anexos verdad.

### Añadir Un Nuevo Caso Problemático

Preferencia:

1. Añadir test unitario pequeño si el caso se puede reproducir con texto artificial.
2. Añadir test de regresión con PDF real si el PDF ya está en `input/`.
3. Documentar fixture externo si el archivo es pesado o no conviene versionarlo.

## Criterio General De Mantenimiento

Cada mejora debería intentar cumplir estas reglas:

- Mantener fronteras claras entre extracción, normalización, asignación y renderizado.
- Añadir tests para cada bug real corregido.
- Evitar excepciones específicas de un certificado salvo que estén justificadas.
- Mantener los detalles visuales de Word centralizados.
- No duplicar constantes de estilo o textos fijos.
- Documentar solo reglas delicadas, no acciones obvias.
