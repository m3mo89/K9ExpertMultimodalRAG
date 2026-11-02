# Auditoría del descubrimiento de razas — 2026-11-02

Precisión y cobertura del vocabulario dinámico (`k9-discovery-v1`, cambio OpenSpec `dynamic-breed-vocabulary`) sobre la enciclopedia de referencia. La lista sale de la tabla `breed_discovery` tras ingerir `docs/references/enciclopedia-perros-caza.pdf` en `data/` con `scripts/stage_reference_corpus.py`.

## Política evaluada

Un encabezado es raza si cumple una de estas condiciones:

- **Evidencia fuerte:** es una semilla curada (`BREED_ALIASES`) o tiene al menos `MINIMUM_SHEET_SECTIONS = 2` hijos distintos que son secciones de ficha (Historia, Aspecto general, Cabeza, Cuerpo, Cola, Manto, El trabajo y las cualidades).
- **Evidencia débil, para fichas cortas sin subsecciones:** tiene al menos `MINIMUM_SIBLING_BREEDS = 2` hermanos con evidencia fuerte (`sibling_breeds`), o un hijo que repite su nombre (`self_caption`: el pie de foto que el detector toma por subencabezado).

Los nombres de sección de ficha y de grupo nunca son razas. El grupo de una raza es su ancestro más cercano que no es raza.

## Resultado

| Medida | Vocabulario fijo (`k9-reference-v1`) | Descubrimiento (`k9-discovery-v1`) |
|---|---:|---:|
| Fragmentos | 786 | 787 |
| Fragmentos con raza | 101 | 552 |
| Fragmentos con grupo | — | 550 |
| Razas distintas | 12 | 77 |
| Razas del gold set recuperadas (12 curadas, 13 alias) | 12 | 12 |
| Encabezados que no son razas registrados como raza | 0 | 0 |

El fragmento adicional se debe a la corrección del detector de encabezados: un encabezado tipográfico ya puede terminar en ")" ("Braco alemán (Kurzhaar)", "Griffon de pelo duro (Korthals)"). Antes se descartaba, y las secciones de ficha del braco alemán colgaban directamente de "Perros de muestra".

Por señal: 43 razas tienen ficha completa (`sheet_sections`), 12 son semillas curadas (10 de ellas también con ficha), 31 son fichas cortas detectadas por sus hermanos (a veces también por su pie de foto) y 1 solo por su pie de foto ("Basset de los Alpes"). Una raza puede tener varias señales.

## Revisión manual

Revisé las 77 entidades: todas son razas o colecciones de razas descritas como una entrada del libro. **No hay falsos positivos** en esta muestra: ningún encabezado de adiestramiento, alimentación, salud o introducción se registró como raza.

**Encabezados compuestos o colectivos (13).** Se registran como una sola entidad, con ficha y citas válidas. Coincide con lo que la decisión D1 del diseño acepta:

- Otros spaniel británicos
- Curly-coated retriever, flat-coated retriever y chesapeake bay retriever
- Langhaariger deutscher, kleiner y grosser münsterländer
- Perros de muestra franceses
- Pudelpointer y stichelhaariger
- Sabueso de sangre de Baviera y sabueso de Hannover
- American foxhound y coonhound negro y fuego
- Gran azul de Gascuña y otras razas francesas
- Pequeño azul de Gascuña y otras razas francesas
- Sabueso austriaco y otras razas austriacas
- Sabueso de Istria y otras razas de la península Balcánica
- Sabuesos noruegos
- Pequeños sabuesos suizos

**Omisiones conocidas (falsos negativos):**

- **Wetterhound:** es la única raza bajo "Perros de agua" y no tiene ficha, así que no tiene hermanos ni secciones.
- **Teckel de pelo corto:** variedad presentada como pie de foto bajo "Teckel", con un solo hermano con evidencia fuerte.
- **"Sabueso Italiano" en "Advertencia":** es una mención introductoria. Es correcto no registrarla.

**Otras observaciones:**

- **"Teckel" (nivel 1) y "Teckel alemán" (nivel 2):** ambos son semillas y se resuelven al mismo nombre canónico. La raza queda sin grupo, porque su único ancestro también es raza. Antes tampoco tenía grupo.
- **Cocker spaniel:** tiene un solo fragmento clasificado. Su ficha en el libro es una entrada corta con foto.
- **Función de caza de los sabuesos:** se decidió que "sabueso" equivale a "rastro" (`FUNCTION_SYNONYMS`). Las razas bajo "Sabuesos de talla grande/mediana/pequeña" quedan como perros de rastro, y los fragmentos con función de caza pasan de 294 a 460.
- **Sin función de caza:** las razas bajo "Perros de caza nórdicos" y "Perros de caza de tipo primitivo" siguen sin ella, porque esos grupos no nombran ninguna función.

## Umbrales

`MINIMUM_SHEET_SECTIONS = 2` no produce falsos positivos en esta muestra. La ficha completa más corta tiene 4 secciones ("Harrier", "Jack russell terrier", "Sabueso de sangre de Baviera…"), así que subir el umbral a 3 no cambiaría nada aquí. Mantengo 2 para no excluir fichas más breves de otros libros. La regla de hermanos aporta 31 razas sin introducir errores.

Limitación: es un solo libro. La precisión en documentos con otra convención de encabezados no está medida.

## Reingesta sin recalcular embeddings

Reseteé la base SQLite y el índice, conservé `data/cache/embeddings` y reingerí:

- **Primera ingesta (caché vacía):** 787 embeddings calculados, 25,9 s.
- **Reingesta tras el reset:** 0 embeddings calculados, 7,7 s.

En ambas, 77 razas descubiertas y 552 fragmentos con raza.

## Evaluación tras la reclasificación

Mismo dataset (`k9-reference` 2.0.0, 22 casos), mismos modelos (`llama3.2:3b`, `nomic-embed-text:latest`) y mismo corpus, ahora ingerido con `k9-discovery-v1`. La línea base es la corrida usada en `model-selection-2026-11-02.md`.

| Métrica (puerta) | Base `20261102T045033Z-E2-7e3065` | Nueva `20261102T064418Z-E2-e31b48` |
|---|---:|---:|
| Recall@5 (G2 ≥ 0.75) | 0.925 | 0.925 |
| Hit@5 (G3 ≥ 0.85) | 0.95 | 0.95 |
| MRR (G4 ≥ 0.60) | 0.808 | 0.808 |
| Precisión de cita (G1 ≥ 0.80) | 0.634 ✘ | **0.576 ✘** |
| Casos fundamentados con cita | 16 | 19 |
| Salida estructurada (G7 ≥ 0.95) | 1.00 | 1.00 |
| Abstención correcta (G5 = 1.0) | 1.0 | 1.0 |
| Falsas abstenciones (G6 ≤ 0.20) | 0.20 | 0.05 |
| Latencia p50 / p95 | 5.08 s / 8.23 s | 4.83 s / 8.76 s |

La recuperación es idéntica, como se esperaba: las preguntas de E2 no usan filtros de raza y el texto de los fragmentos no cambió. Las diferencias están en la generación. Hay más respuestas fundamentadas y menos abstenciones falsas, pero la precisión de cita baja de 0.634 a 0.576. Ninguna de las dos cumple G1.

Cada corrida es una sola ejecución de `llama3.2:3b` con la temperatura por defecto, así que estas diferencias no se pueden atribuir al cambio de vocabulario sin repetir las corridas. Lo registro como observación, no como mejora ni como regresión.

Capas (`20261102T064628Z-LAYERS-6a2ec1` frente a `20261102T052505Z-LAYERS-74e05f`): guardrails, router, caché, agente y BreedMatch dan los mismos agregados:

- BreedMatch: estado, hallazgos y orden con 1.0; precisión de página de cita 0.931.
- Agente: decisión final 0.833.
