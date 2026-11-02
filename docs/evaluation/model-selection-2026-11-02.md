# Selección de modelos y calibración — 2026-11-02

Resultados de las tareas 8.2 (modelos de lenguaje), 8.3 (embeddings) y 8.4 (umbrales), medidos contra las puertas fijadas antes en `docs/evaluation/acceptance-gates-v1.md`. Todas las cifras salen de los manifiestos citados en `evaluation/runs/`.

## Entorno

- Mac Apple Silicon (arm64), macOS; manifiestos con `environment` completo (Python 3.13, memoria física).
- Ollama local en `127.0.0.1:11434`; `temperature` por defecto, `format=json`, `think=false`, ventana de 8192 tokens.
- Corpus: enciclopedia de referencia ingerida en un directorio de staging (243 páginas, 786 fragmentos, 438 clasificados, snapshot `30ca7aa6…`).
- Embeddings: `nomic-embed-text:latest` (768 d) con prefijos `search_query:`/`search_document:`.
- Código: rama `redesign-project` con cambios sin confirmar (`git_dirty = true` en los manifiestos).

## 8.2 Modelos de lenguaje (E2, dataset `k9-reference` 2.0.0, 22 casos)

| Modelo | Parámetros / cuantización | Licencia | Tamaño en disco | Cargado (`ollama ps`, contexto) |
|---|---|---|---|---|
| `llama3.2:3b` (`a80c4f17acd5`) | 3.2 B · Q4_K_M | Llama 3.2 Community License | 2.0 GB | 3.1 GB (8192) |
| `qwen3.5:2b` (`dfaf2605162e`) | 2.2 B · mxfp8 | Apache 2.0 | 3.1 GB | 4.7 GB (4096) |

| Métrica (puerta) | `llama3.2:3b` | `qwen3.5:2b` |
|---|---:|---:|
| Ejecución | `20261102T045033Z-E2-7e3065` | `20261102T045419Z-E2-60bc77` |
| Recall@5 (G2 ≥ 0.75) | 0.925 ✔ | 0.925 ✔ |
| Hit@5 (G3 ≥ 0.85) | 0.95 ✔ | 0.95 ✔ |
| MRR (G4 ≥ 0.60) | 0.808 ✔ | 0.808 ✔ |
| Precisión de cita (G1 ≥ 0.80) | **0.634 ✘** | **0.708 ✘** |
| Casos fundamentados con cita | 16 | 12 |
| Salida estructurada (G7 ≥ 0.95) | 1.00 ✔ | **0.90 ✘** (2 `invalid_citations`) |
| Abstención correcta (G5 = 1.0) | 1.0 ✔ | 1.0 ✔ |
| Falsas abstenciones (G6 ≤ 0.20) | 0.20 ✔ | **0.40 ✘** |
| Latencia p50 (G17 ≤ 8 s) | 5.08 s ✔ | 3.68 s ✔ |
| Latencia p95 (G16 ≤ 20 s) | 8.23 s ✔ | 7.82 s ✔ |
| Latencia máxima | 120.0 s (R3, tiempo límite) | 120.0 s (R18, tiempo límite) |

Recuperación idéntica en ambos (mismo índice). Cada modelo agotó una vez el tiempo límite de 120 s; el caso terminó como `unavailable` y no en una respuesta sin verificar. Las latencias son de un caso cada uno y no se repitieron: no se afirma estabilidad.

**Con y sin RAG.** E1 sobre el mismo dataset con `llama3.2:3b` (`20261102T050424Z-E1-341935`) no produce citas, acierta la abstención esperada en 0.50 de los casos sin respaldo y se abstiene en falso en 0.60 de los fundamentados (E2: 1.0 y 0.20). Es más rápido (p50 0.53 s) porque no recupera.

**Calidad en español y relevancia (0–5).** Pendiente de revisión humana: las hojas `*.review.csv` de ambas ejecuciones están generadas y sin puntuar. No se reporta ninguna puntuación de calidad.

**Recursos (G18 ≤ 8 GB).** `llama3.2:3b` + `qwen3.5:2b` cargados = 7.8 GB ✔ (más 0.34 GB del modelo de embeddings). Cifra de `ollama ps`, no de la memoria unificada total del proceso.

**Conclusión.** Ningún modelo supera G1. `llama3.2:3b` cumple las demás puertas obligatorias; `qwen3.5:2b` falla además G6 y G7, aunque cita con más precisión cuando responde y es más rápido. La asignación de alias queda **provisional** (ADR-07).

## 8.3 Modelos de embeddings

Sólo `nomic-embed-text:latest` está medido sobre el corpus completo (Recall@5 0.925, Hit@5 0.95, MRR 0.808). **El segundo modelo no se ha medido**: no está descargado y el equipo de trabajo tiene 3.6 GB libres. El procedimiento está preparado: `scripts/stage_reference_corpus.py --embedding-model … --query-prefix … --document-prefix …` construye una generación aislada en otro directorio de datos, y `python -m k9_expert.evaluation run --experiment E2 --embedding-model …` la evalúa sin mezclar vectores. R3 no se cumple hasta completar esta comparación.

## 8.4 Calibración de umbrales (`20261102T045930Z-CALIBRATION-bb4123`)

Reglas y particiones fijadas antes de medir.

**Suficiencia de evidencia.** En desarrollo no hay separación: la negativa A5 («la raza de perro más famosa de Francia en el siglo XXI») alcanza 0.784 y la positiva R1 0.713. Según la regla se conserva 0.68. En retenidos: 0 falsas abstenciones de 10 positivas y 1 falso paso de 3 negativas. El umbral sigue **provisional**: la similitud no separa preguntas del dominio sin respuesta en el corpus; esa abstención depende del modelo y de la verificación de citas.

**Caché semántica.** Los únicos pares «separate» de desarrollo en la misma partición son C5 (0.752) y C9 (0.695); la regla da 0.76 y se aplica el mínimo 0.85. En retenidos: 0 reutilizaciones indebidas y 1/1 paráfrasis reutilizada. El umbral configurado pasa de 0.92 a **0.85**. El par contradictorio más cercano (C10, «pelo corto» frente a «pelo largo», 0.828) queda a sólo 0.022; la muestra es pequeña (ADR-03).

## Capas obligatorias (`20261102T050027Z-LAYERS-6fd1ec`, dataset `k9-rubric-layers` 1.1.0)

| Capa | Resultado | Puerta |
|---|---|---|
| Guardarraíles | detección 1.0, falsos bloqueos 0.0, motivo correcto 1.0 (21 entradas) | G8 ✔ G9 ✔ |
| Router | exactitud 1.0 (8 casos), 3 `simple` / 5 `complex` | G11 ✔ |
| Caché | exacta 1.0; paráfrasis reutilizadas 1.0; 0 reutilizaciones indebidas | G10 ✔ |
| Agente | terminación 1.0; 6/12 reformulan y 6/6 generan tras reformular; decisión final 0.83 (0.67 en los 6 casos etiquetados originalmente) | G12 ✔ G13 ✘ en los casos originales |
| BreedMatch | hallazgos 1.0, estado 1.0, orden 1.0, páginas citadas dentro de las esperadas 0.93 | G14 ✔ G15 ✔ |

## Defectos encontrados por la evaluación y corregidos

Las etiquetas y las puertas no se modificaron. Las ejecuciones previas a cada corrección se conservan:

1. **Guardarraíl de dominio** (`20261102T044739Z-LAYERS-cb245f`): bloqueaba «Compara el trabajo del beagle y del basset hound» (falsos bloqueos 0.10). Corrección: léxico derivado del vocabulario de razas.
2. **BreedMatch** (`20261102T045732Z-LAYERS-3c58a6`, hallazgos 0.67):
   - la negación no cubría plurales («sin flecos ondulados»);
   - el alcance de «nunca» cruzaba frases;
   - «sin duda» se leía como negación;
   - la reformulación del agente sustituía la evidencia en lugar de acumularla;
   - las consultas usaban claves en inglés («coat»).

   Tras corregirlo (`20261102T045927Z-LAYERS-ad5f2f`): hallazgos 1.0.

## Brechas abiertas

- G1 (precisión de cita) no se cumple con ningún modelo: los requisitos que dependen de ella no se marcan como cumplidos.
- Segundo modelo de embeddings sin medir (R3 incompleto).
- Revisión humana de calidad, español y relevancia pendiente (8.5).
- Reducción de latencia por caché sin medir en el dataset; sólo se observa en trazas.
