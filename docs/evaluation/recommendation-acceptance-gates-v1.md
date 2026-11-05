# Puertas de aceptación para recomendación guiada v1

Antes de habilitar el flujo guiado por defecto en una Mac de 16 GB:

| # | Puerta | Criterio medible | Evidencia |
|---|---|---|---|
| G1 | Reproducibilidad | Repetición idéntica de perfil, snapshot y política produce el mismo orden y desglose. | `test_recommendation.py`, `test_recommendation_api.py` |
| G2 | Perfil incompleto | Los casos incompletos no ejecutan puntuación ni generación (`status = incomplete`). | `test_incomplete_profile_never_scores_or_generates` |
| G3 | Desconocidos | Ningún resultado convierte evidencia ausente en coincidencia o penalización. | `test_recommendation.py`, métrica `unknown_handling` |
| G4 | Procedencia | Cada afirmación documentada resuelve a fuente y página; las contradicciones son visibles. | `test_structured_knowledge.py` |
| G5 | Evaluación humana | Al menos un conjunto revisado por especialistas, con acuerdo y desacuerdo registrados; sin aprobación por LLM. | `docs/evaluation/recommendation-human-rubric-v1.md` |
| G6 | Suites | Backend, frontend y E2E/Axe pasan. | `make test lint typecheck web-check web-test web-e2e` |
| G7 | Latencia local (provisional) | p95 de validación de perfil ≤ 100 ms y de recomendación determinista ≤ 500 ms con narrativa desactivada. | Línea base abajo |
| G8 | Migración | Respaldo previo, actualización verificada y restauración para el binario anterior. | `test_v7_upgrade_backs_up_preserves_v1_data_and_rollback_restores_old_schema` |
| G9 | Utilidad mínima | Con el corpus de referencia y afirmaciones aprobadas por especialistas, al menos un perfil del conjunto de evaluación produce resultados (no solo abstención). | `evaluation/datasets/k9-recommendation-v1.json` |

Los umbrales de G7 son provisionales: se fijaron con una sola máquina y deben revisarse si cambia el hardware objetivo.

## Línea base local (2026-11-03)

- **Hardware:** Apple M3 Pro, 18 GB (la más cercana disponible a la Mac objetivo de 16 GB).
- **Corpus:** `enciclopedia-perros-caza.pdf` ingerido en un directorio de staging: 243 páginas, 787 fragmentos, 552 con raza, 77 razas descubiertas. Ingesta 27 s con caché de embeddings caliente; RSS pico 298 MB.
- **Carga de conocimiento:** las 391 afirmaciones candidatas del extractor por reglas se aprobaron con revisor `load-test` **solo para medir latencia**; no son revisión experta.
- **Medición:** 200 peticiones en proceso (`TestClient`) tras un calentamiento, perfil completo de 5 respuestas, todas las razas, narrativa desactivada.

| Operación | p50 | p95 | máx |
|---|---|---|---|
| `POST /api/v2/hunter-profiles/validate` | 1.2 ms | 1.4 ms | 2.0 ms |
| `POST /api/v2/recommendations` | 31.5 ms | 35.7 ms | 58.6 ms |

RSS pico del proceso de medición: 136 MB. G7 se cumple. La narrativa con Ollama no se midió: está desactivada por defecto y su latencia la domina el modelo.

## Estado actual

G1–G4, G6, G7 y G8 se cumplen. **G9 se cierra por decisión del autor del proyecto (2026-11-04), con una desviación de su criterio**: el corpus de referencia produce resultados, pero con afirmaciones publicadas automáticamente y no aprobadas por especialistas, y sobre perfiles ejecutados en la aplicación, no sobre el conjunto de evaluación (ver «Ejecución de puertas (2026-11-04)»). Esto demuestra que hay resultados, no que sean correctos. **G5 no se cumple**: el conjunto de evaluación no tiene juicios de especialistas.

## Ejecución de puertas (2026-11-04)

Tras `automate-breed-knowledge-publication`, con la política `recommendation-v3`. Corpus ingerido en un directorio temporal; seis perfiles recorridos en el navegador, en la interfaz real contra la API real, en un Apple M3 Pro de 18 GB.

| Perfil (presa / trabajo / terreno) | Estado | Razas | Citas en pantalla | Aspectos «No documentado» |
|---|---|---|---|---|
| Venado / Seguir un rastro / Monte denso | `completed` | 3 | 17 | 2 |
| Aves / Señalar la pieza / Campo abierto | `completed` | 3 | 19 | 1 |
| Aves / Cobrar / Humedales | `completed` | 3 | 18 | 0 |
| Jabalí / Levantar piezas / Montaña | `completed` | 3 | 12 | 3 |
| Conejo / Seguir un rastro / Terreno accidentado | `completed` | 3 | 10 | 3 |
| Liebre / Trabajar en agua / Montaña | `completed` | 3 | 6 | 3 |

Los seis muestran el aviso de extracción automática y ninguno produjo una abstención. No se comprobó que las razas sean adecuadas ni que cada página citada respalde la afirmación.

| Puerta | Resultado | Evidencia |
|---|---|---|
| Utilidad con el corpus real (G9) | **Cerrada por decisión del autor**, con la desviación indicada en «Estado actual» | Tabla anterior |

## Ejecución de puertas (2026-11-03)

| Puerta de lanzamiento | Resultado | Evidencia |
|---|---|---|
| Repetición de perfil fijo | Pasa | `test_conflicts_do_not_create_compatibility_and_order_is_reproducible`, `test_recommendation_api_is_deterministic_without_ollama` |
| Ollama no disponible | Pasa: mismo desglose, `narrative_unavailable` | `test_recommendation_api_is_deterministic_without_ollama`, `test_unverified_narrative_cannot_change_api_ranking` |
| Ingesta adversarial | Pasa: instrucciones en el PDF, JSON inválido e IDs inventados se descartan | `test_ollama_extraction_accepts_only_closed_grounded_json`, `test_review_requires_identity_snapshot_and_existing_evidence` |
| Conjunto experto `k9-recommendation-v1` | **No evaluable**: 1 caso (abstención correcta, campos faltantes correctos), 0 juicios de especialistas | `evaluation/datasets/k9-recommendation-v1.json` |
| Utilidad con el corpus real (G9) | **Falla**: con todas las candidatas aprobadas, todas las razas se abstienen | Línea base anterior |

## Limitaciones vigentes

- No hay afirmaciones revisadas por especialistas ni juicios expertos; el conjunto de evaluación solo cubre un caso de abstención.
- `experience` y `daily_availability` no se evalúan, porque el corpus no permite documentarlas.
- La precisión del extractor por reglas no está medida: no hay ninguna muestra etiquetada en el repositorio. Las afirmaciones erróneas pueden influir en los resultados.
- Los pesos y el umbral de cobertura son configuración de diseño sin calibración experta.

Con G5 sin cumplir, el flujo guiado es el predeterminado sin validación de especialistas; los resultados lo advierten y citan la página para que se pueda comprobar.
