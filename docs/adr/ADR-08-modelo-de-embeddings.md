# ADR-08: Modelo de embeddings

- **Estado:** Aceptada (2026-11-06). Se compararon dos modelos sobre el mismo corpus y dataset.

**Contexto.** La recuperación (C5) y la caché semántica (C4) dependen del modelo de embeddings. El corpus está en español y cada snapshot registra la identidad de embeddings: cambiar de modelo exige una generación de índice nueva.

**Decisión.** Mantener `nomic-embed-text:latest`: 137 M parámetros, F16, 768 dimensiones, Apache 2.0, prefijos `search_query:`/`search_document:`.

**Alternativas.** Se evaluó `bge-m3:latest` por su soporte multilingüe: 566.7 M parámetros, F16, 1024 dimensiones y licencia MIT. `embeddinggemma` y `mxbai-embed-large` se consideraron, pero no se midieron. Cada candidato se indexó en un directorio aislado para no mezclar dimensiones ni cachés.

**Evidencia.** Mismo dataset `k9-reference` 2.0.0 (22 casos), mismo corpus y mismos parámetros de recuperación:

| Métrica | `nomic-embed-text` | `bge-m3` |
|---|---:|---:|
| Dimensiones | 768 | 1024 |
| Recall@1 | 0.575 | **0.625** |
| Recall@3 | **0.925** | 0.900 |
| Recall@5 | 0.925 | 0.925 |
| Hit@5 | 0.950 | 0.950 |
| MRR | 0.808 | **0.825** |
| Tiempo de embeddings | **16.1 s** | 34.4 s |
| Tamaño del modelo | **274 MB** | 1.2 GB |

Ejecuciones: Nomic `evaluation/runs/20261102T045033Z-E2-7e3065.json`; BGE-M3 `evaluation/runs/20261107T033817Z-E2-aad176.json`; calibración BGE-M3 `evaluation/runs/20261107T033904Z-CALIBRATION-b3dbb8.json`.

**Consecuencias.** Ambos modelos superan G2–G4 y empatan en Recall@5 e Hit@5. BGE-M3 mejora MRR en 0.017 y Recall@1 en 0.05, pero Nomic obtiene mejor Recall@3, tarda aproximadamente la mitad en la ingesta y ocupa cerca de una cuarta parte. La mejora de BGE-M3 no justifica su costo para este corpus, por lo que Nomic permanece activo. La calibración también demostró que los umbrales de suficiencia y caché no son transferibles entre modelos: BGE-M3 requeriría recalibración y un dataset con mejor separación antes de publicarse.
