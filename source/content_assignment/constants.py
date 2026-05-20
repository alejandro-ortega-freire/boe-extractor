SMALL_CONTENT_SPLIT_PENALTY = 4.0
MAX_CONTENT_PARTS = 2
ASSIGNMENT_WINDOW = 1
PARTITION_DIVERSITY_THRESHOLD = 2
MAX_AUTOMATIC_CONTENT_PARTS = 2
FUSION_CORE_BONUS = 3.0
FUSION_SUPPORT_BONUS = 2.0
FUSION_PHASE_BONUS = 1.0
HIGH_CONFIDENCE_THRESHOLD = 14.0
MEDIUM_CONFIDENCE_THRESHOLD = 6.0

STOPWORDS = {
    "a", "al", "ante", "asi", "cada", "como", "con", "contra", "de", "del",
    "desde", "el", "en", "entre", "e", "la", "las", "lo", "los", "o", "para",
    "por", "que", "se", "segun", "sin", "sobre", "su", "sus", "un", "una",
    "unas", "unos", "y",
    "accion", "acciones", "actividad", "actividades", "adecuado", "adecuados",
    "aplicacion", "aplicaciones", "caracteristicas", "caso", "criterio",
    "criterios", "datos", "diferentes", "documento", "documentos", "forma",
    "funcion", "funciones", "informacion", "mediante", "necesario",
    "procedimiento", "procedimientos", "proceso", "procesos", "relacion",
}

GENERIC_PEDAGOGICAL_TERMS = {
    "actividad", "actividades", "aprendizaje", "didactico", "didactica",
    "ensenanza", "formacion", "formativo", "formativa", "metodologia",
    "metodologico", "metodologica", "objetivo", "objetivos", "recurso",
    "recursos", "resultado", "resultados",
}

DOMAIN_SYNONYMS = {
    "email": ["correo", "electronico", "mensaje"],
    "correo": ["email", "electronico", "mensaje", "correspondencia"],
    "correspondencia": ["correo", "mensaje"],
    "mensaje": ["correo", "correspondencia"],
    "ofimatica": ["procesador", "textos", "hoja", "calculo", "presentacion"],
    "procesador": ["texto", "textos", "documento"],
    "textos": ["procesador", "documento", "redaccion"],
    "plantilla": ["modelo", "documento"],
    "plantillas": ["modelo", "documento"],
    "base": ["datos"],
    "datos": ["base", "registro"],
    "hoja": ["calculo"],
    "calculo": ["hoja"],
    "presentacion": ["diapositiva", "grafica"],
    "presentaciones": ["diapositiva", "grafica"],
    "archivo": ["fichero", "carpeta"],
    "archivos": ["ficheros", "carpetas"],
    "carpeta": ["archivo", "fichero"],
    "carpetas": ["archivos", "ficheros"],
    "seguridad": ["confidencialidad", "integridad", "proteccion"],
    "urgencia": ["emergencia"],
    "urgencias": ["emergencias"],
    "emergencia": ["urgencia"],
    "emergencias": ["urgencias"],
}

TECHNICAL_EXPRESSIONS = {
    "aula virtual",
    "base datos",
    "bases datos",
    "calidad acciones",
    "carta presentacion",
    "correo electronico",
    "curriculum vitae",
    "entorno virtual",
    "escala likert",
    "firma electronica",
    "hoja calculo",
    "hojas calculo",
    "lista cotejo",
    "plan tutorial",
    "pizarra digital",
    "procesador textos",
    "programacion didactica",
    "prueba practica",
    "prueba teorica",
    "registro calificaciones",
    "soporte vital",
    "soporte vital avanzado",
    "soporte vital basico",
    "sistema operativo",
    "tabla especificaciones",
    "tratamiento textos",
}

SEMANTIC_CORES = {
    "programacion": {"programacion", "didactica", "temporalizacion", "unidad", "cronograma"},
    "evaluacion": {"evaluacion", "prueba", "pruebas", "item", "items", "rubrica", "cotejo", "escala", "calificacion"},
    "fundamentos": {"estructura", "estructuras", "normativa", "marco", "sistema", "certificado", "certificados", "fundamento", "fundamentos"},
    "tutoria": {"tutoria", "tutorial", "seguimiento", "alumno", "alumnos", "orientacion", "asesoramiento"},
    "material": {"material", "materiales", "grafico", "graficos", "multimedia", "impreso", "presentacion"},
    "virtual": {"virtual", "online", "linea", "foro", "foros", "chat", "videotutorial", "plataforma"},
    "correo": {"correo", "electronico", "mensaje", "correspondencia"},
    "ofimatica": {"procesador", "textos", "calculo", "presentacion", "archivo", "carpeta"},
    "calidad": {"calidad", "innovacion", "actualizacion", "mejora", "revision"},
    "empleo": {"empleo", "curriculum", "entrevista", "profesional", "ocupacion", "competencia"},
    "seguridad": {"seguridad", "prevencion", "riesgos", "proteccion", "confidencialidad"},
}

VERB_PHASES = {
    "conceptual": {
        "analizar", "clasificar", "definir", "describir", "diferenciar",
        "enumerar", "identificar", "indicar", "reconocer",
    },
    "production": {
        "adaptar", "construir", "disenar", "elaborar", "organizar",
        "redactar", "seleccionar", "secuenciar",
    },
    "use": {
        "aplicar", "comprobar", "manejar", "registrar", "supervisar",
        "ubicar", "utilizar",
    },
    "evaluation": {
        "actualizar", "corregir", "evaluar", "mejorar", "perfeccionar",
        "proponer", "revisar",
    },
    "support": {
        "asesorar", "fomentar", "orientar", "promover", "tutorizar",
    },
}

MODALITY_SUPPORTS = {
    "presencial": {"presencial", "aula"},
    "online": {"online", "linea", "virtual", "plataforma", "foro", "chat", "videotutorial"},
    "graphic": {"grafico", "graficos", "imagen", "imagenes", "tipografia", "reticula"},
    "multimedia": {"multimedia", "diapositiva", "sonido", "animacion", "hipervinculo"},
    "text": {"texto", "textos", "procesador", "redaccion", "documento"},
}

NEGATIVE_KEYWORD_GROUPS = [
    {"correo", "electronico", "mensaje", "correspondencia"},
    {"texto", "textos", "procesador", "redaccion", "plantilla", "plantillas"},
    {"calculo", "hoja", "hojas"},
    {"base", "bases", "datos", "registro", "registros"},
    {"presentacion", "presentaciones", "diapositiva", "grafica", "graficas"},
    {"archivo", "archivos", "fichero", "ficheros", "carpeta", "carpetas"},
    {"seguridad", "confidencialidad", "integridad", "proteccion"},
    {"urgencia", "urgencias", "emergencia", "emergencias"},
]

PRACTICAL_CASE_MARKERS = (
    "en un supuesto practico",
    "ante un supuesto practico",
    "a partir de un supuesto practico",
)
