# Paquete de evidencia para el informe técnico (15–25 páginas)

Correspondencia entre cada apartado de la sección 11.1 del enunciado y la evidencia versionada. Toda cifra del informe debe citar uno de estos archivos; lo que aquí figura como pendiente no puede presentarse como resultado.

| § | Apartado del informe | Fuente de la evidencia | Pendiente |
|---|---|---|---|
| 1 | Portada y resumen | Este documento y `docs/rubric/traceability.md` | Redacción |
| 2 | Idea del producto (K9 BreedMatch): usuario, problema, resultado, propuesta de valor y originalidad | `README.md`; `openspec/changes/adapt-k9-expert-to-rubric/proposal.md`; ADR-09 | Ficha aprobada por el docente |
| 3 | Dominio y corpus (origen, tamaño, licencia) | `README.md` (Corpus); `evaluation/datasets/k9-reference-v2.json` (SHA-256, 243 páginas); ingesta: 786 fragmentos, 438 clasificados, 16 páginas que requerirían OCR | Confirmar el permiso de uso del PDF |
| 4 | Requisitos y atributos de calidad medibles | `docs/evaluation/acceptance-gates-v1.md` (G1–G18) | — |
| 5 | Arquitectura (vistas estructurales) | `docs/architecture/diagrams.md`, diagramas 1–5 | Exportar a imagen |
| 6 | Comportamiento (secuencias) | `docs/architecture/diagrams.md`, diagramas 6–10 | Exportar a imagen |
| 7 | Selección de modelos y enrutamiento | `docs/evaluation/model-selection-2026-11-02.md`; ADR-02, ADR-07, ADR-08; ejecuciones E2 `7e3065` y `60bc77` | Segundo modelo de embeddings; puntuación humana de calidad (0–5) |
| 8 | Diseño de cada capa | ADR-01, ADR-03, ADR-04, ADR-05, ADR-06, ADR-09; `docs/rubric/traceability.md` | — |
| 9 | ADR (≥ 6) | `docs/adr/` (9 ADR; 2 provisionales) | — |
| 10 | Evaluación y análisis de errores | `evaluation/runs/` (E1 `c29f7a`, E2 `7e3065` y `60bc77`, LAYERS `cb245f` → `3c58a6` → `ad5f2f` → `6fd1ec`, CALIBRATION `bb4123`); sección «Defectos encontrados» de `model-selection-2026-11-02.md` | Revisión humana. Sin RAG (E1 `20261102T050424Z-E1-341935`, llama3.2:3b): sin citas, abstención correcta 0.5, falsas abstenciones 0.6; con RAG (E2 `7e3065`): 1.0 y 0.2 |
| 11 | Limitaciones, riesgos y trabajo futuro | `docs/operations/local-operations.md` §11; riesgos de ADR-03, ADR-05, ADR-07; brechas de la matriz | — |
| 12 | Referencias y anexos (README, API) | `README.md`; OpenAPI en `/openapi.json` | Exportar OpenAPI |

## Ensayo de la demostración (2026-11-02, con red disponible)

Servicio levantado con `make serve` sobre el directorio de staging. Comandos de `README.md` y observaciones:

| Paso | Observación |
|---|---|
| BreedMatch (cobro + impermeable; labrador frente a golden) | `completed`, ruta `complex` (`large_evidence_set`), `qwen3.5:2b`, 13.3 s, guardarraíles `allow/allow` |
| Misma petición | caché `exact`, 20 ms |
| Paráfrasis («cobro de piezas») | caché `semantic`, similitud 0.934 |
| Criterio con inyección | `rejected`, `block:prompt_injection_detected` |
| BreedMatch de una raza y un criterio | ruta `simple`, `llama3.2:3b`, 2.6 s |
| Chat: pelo del golden retriever | `grounded`, citas p. 167, ruta `simple` |
| Chat: «jauría» | 2 iteraciones del agente, ruta `complex` (`agent_reformulation`), el modelo se abstuvo |
| Retroalimentación, `/configuration`, `/admin/metrics`, `/openapi.json` | 201, 200, agregados por capa con utilidad por ruta y modelo, 200 |

Observación de calidad: la síntesis de `qwen3.5:2b` en el primer paso parafrasea con imprecisión («su información sobre cobertura ("no impermeable")») aunque sus citas son válidas. La barrera de salida comprueba citas, no la fidelidad de cada frase; se declara como limitación.

## Uso declarado de asistentes de IA

El desarrollo usó Claude Code (Anthropic) como asistente de programación: implementación guiada por los artefactos de OpenSpec, pruebas, scripts de evaluación, borradores de ADR y diagramas, y construcción asistida de los datasets. Toda etiqueta de dataset producida con asistencia figura con el revisor «Claude Code (agent-assisted; pending human sign-off)» y requiere firma humana antes de usarse como evidencia final. El sistema entregado no llama a ningún modelo en la nube.
