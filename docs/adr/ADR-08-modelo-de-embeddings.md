# ADR-08: Modelo de embeddings

- **Estado:** **Provisional** (2026-11-02). Falta medir el segundo modelo exigido por R3.

**Contexto.** La recuperación (C5) y la caché semántica (C4) dependen del modelo de embeddings. El corpus está en español y cada snapshot registra la identidad de embeddings: cambiar de modelo exige una generación de índice nueva.

**Decisión (provisional).** `nomic-embed-text:latest`: 137 M parámetros, F16, 768 dimensiones, Apache 2.0, prefijos `search_query:`/`search_document:`.

**Alternativas.** `embeddinggemma`, `mxbai-embed-large` y `bge-m3`: candidatos sin medir. El procedimiento de comparación aislada está preparado (`scripts/stage_reference_corpus.py --embedding-model … --query-prefix … --document-prefix …` y `python -m k9_expert.evaluation run --experiment E2 --embedding-model …`). No se ejecutó porque el modelo no está descargado y el equipo tiene 3.6 GB libres.

**Evidencia.** E2 con `nomic-embed-text` (`evaluation/runs/20261102T045033Z-E2-7e3065.json`): Recall@5 0.925, Hit@5 0.95, MRR 0.808, todas las puertas de recuperación (G2–G4) superadas. Ingesta completa de 786 fragmentos en 16.1 s de embeddings.

**Consecuencias.** La recuperación cumple sus puertas, pero R3 queda incompleto hasta medir un segundo modelo con el mismo dataset. Si el segundo modelo gana, se publica como generación nueva (ADR-06) y se recalibran los umbrales de ADR-03 y ADR-05.
