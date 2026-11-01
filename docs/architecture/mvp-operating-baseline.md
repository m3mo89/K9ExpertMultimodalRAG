# Baseline operativo del MVP

La configuración versionada en `config/k9.defaults.toml` reúne los resultados y límites iniciales de los spikes. No sustituye las mediciones de calificación final.

## Selecciones provisionales

| Área | Valor inicial | Evidencia |
|---|---|---|
| Generación | alias `text-default` → `llama3.2:3b` | `local-generation-baseline-2026-11-01.md`; mejor duración en la prueba mínima, pero exige verificación de citas |
| Embeddings | alias `embedding-default` → `nomic-embed-text:latest`, 768d | `local-embedding-baseline-2026-11-01.md`; rango 1 en la prueba de recuperación mínima |
| Índice | ChromaDB persistente, generaciones aisladas | `scripts/validate_chroma_spike.py` pasó filtros, persistencia y restauración |
| Concurrencia | un trabajador de ingesta | límite conservador para la Mac objetivo; debe medirse en calificación |
| OCR | por página y selectivo | `ocr-extraction-baseline-2026-11-01.md` |

## Límites no garantizados

Los límites de archivo, páginas, timeout, lote, contexto y retención son salvaguardas configurables. Se deberán ajustar tras medir la ingestión de la enciclopedia y la carga concurrente; no representan promesas de rendimiento.

## Incompatibilidades de snapshot

Un cambio en modelo de embeddings, dimensión, normalización, prefijos de tarea, extractor o fragmentación exige crear una generación de índice compatible. Las consultas deben registrar el alias resuelto y el snapshot utilizados.

## Bloqueadores conocidos no funcionales

- Tesseract no está disponible todavía; la extracción directa sigue siendo viable para el PDF inicial.
- La medición completa de memoria unificada y percentiles exige instrumentación de host durante la calificación end-to-end.
- El alias de generación no queda definitivamente aprobado hasta ejecutar todos los casos R1–R10 con recuperación real y verificación de citas.
