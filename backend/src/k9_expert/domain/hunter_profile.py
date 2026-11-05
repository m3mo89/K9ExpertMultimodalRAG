"""Controlled hunter-profile vocabulary and user-facing help for recommendation v2."""

from __future__ import annotations

from dataclasses import dataclass

PROFILE_SCHEMA_VERSION = "2.0"
PROFILE_TRANSLATOR_VERSION = "hunter-profile-v2"
# Dimensions the corpus can document; other answers are accepted but never scored.
EVALUABLE_DIMENSIONS = frozenset({"prey", "modality", "terrain"})
ANY_PREY = "varias_especies"


@dataclass(frozen=True, slots=True)
class ProfileField:
    key: str
    label: str
    values: tuple[str, ...]
    required: bool
    multiple: bool
    help: dict[str, str]


FIELDS = (
    ProfileField(
        "prey", "¿Qué desea cazar?",
        ("venado", "jabalí", "conejo", "liebre", "aves", "varias_especies"),
        True, True, {},
    ),
    ProfileField(
        "modality", "¿Qué espera que haga el perro?",
        ("rastreo", "rastro_herido", "muestra", "cobro", "levantamiento", "agua"),
        True, True,
        {
            "rastreo": "Seguir el olor o rastro dejado por una pieza.",
            "rastro_herido": "Localizar una pieza herida siguiendo su rastro.",
            "muestra": "Localizar y señalar la pieza sin levantarla.",
            "cobro": "Recuperar y entregar la pieza abatida.",
            "levantamiento": "Buscar y hacer salir la pieza de su refugio.",
            "agua": "Buscar o cobrar piezas en humedales y agua.",
        },
    ),
    ProfileField(
        "terrain", "¿Dónde caza principalmente?",
        ("monte_denso", "bosque", "campo_abierto", "montana", "accidentado", "humedal"),
        True, True, {},
    ),
    ProfileField(
        "experience", "¿Qué experiencia tiene con perros de trabajo?",
        ("principiante", "intermedia", "avanzada"), False, False, {},
    ),
    ProfileField(
        "daily_availability", "¿Cuánto tiempo diario puede dedicar a ejercicio y entrenamiento?",
        ("menos_1h", "1_2h", "mas_2h"), False, False, {},
    ),
    ProfileField(
        "hunting_frequency", "¿Con qué frecuencia caza?",
        ("ocasional", "mensual", "semanal", "frecuente"), False, False, {},
    ),
    ProfileField(
        "climate", "¿Cuál es el clima habitual?",
        ("frio", "templado", "calido", "humedo"), False, True, {},
    ),
    ProfileField(
        "space", "¿Qué espacio tiene disponible?",
        ("reducido", "medio", "amplio"), False, False, {},
    ),
    ProfileField(
        "care_preference", "¿Qué nivel de cuidados prefiere?",
        ("bajo", "medio", "sin_preferencia"), False, False, {},
    ),
)

FIELD_BY_KEY = {field.key: field for field in FIELDS}
REQUIRED_FIELDS = tuple(field.key for field in FIELDS if field.required)


def validate_answer(key: str, values: tuple[str, ...]) -> None:
    field = FIELD_BY_KEY.get(key)
    if field is None:
        raise ValueError(f"profile_field_unsupported:{key}")
    if not values or (not field.multiple and len(values) != 1):
        raise ValueError(f"profile_cardinality_invalid:{key}")
    if any(value not in field.values for value in values):
        raise ValueError(f"profile_value_unsupported:{key}")
    if len(set(values)) != len(values):
        raise ValueError(f"profile_value_duplicate:{key}")
