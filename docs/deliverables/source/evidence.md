# Matriz de evidencia de los entregables

| Afirmación | Valor usado | Fuente versionada |
|---|---:|---|
| Corpus | 243 páginas | `README.md`; `evaluation/datasets/k9-reference-v2.json` |
| Fragmentos de la corrida Nomic | 786 | `evaluation/runs/20261102T045033Z-E2-7e3065.json` |
| Nomic Recall@5 / Hit@5 / MRR | 0.925 / 0.950 / 0.808 | `evaluation/runs/20261102T045033Z-E2-7e3065.json` |
| BGE-M3 Recall@5 / Hit@5 / MRR | 0.925 / 0.950 / 0.825 | `evaluation/runs/20261107T033817Z-E2-aad176.json` |
| Llama precisión de cita / p50 | 0.634 / 5.08 s | `evaluation/runs/20261102T045033Z-E2-7e3065.json` |
| Qwen precisión de cita / p50 | 0.708 / 3.68 s | `evaluation/runs/20261102T045419Z-E2-60bc77.json` |
| Guardrails | detección 1.0; falsos bloqueos 0.0 | `evaluation/runs/20261102T050027Z-LAYERS-6fd1ec.json` |
| Router | exactitud 1.0 | `evaluation/runs/20261102T050027Z-LAYERS-6fd1ec.json` |
| Caché | exacta 1.0; paráfrasis 1.0; indebidas 0 | `evaluation/runs/20261102T050027Z-LAYERS-6fd1ec.json` |
| BreedMatch | hallazgos, estado y orden 1.0; páginas 0.93 | `evaluation/runs/20261102T050027Z-LAYERS-6fd1ec.json` |
| Latencia observada de caché | 13.3 s → 20 ms | `docs/rubric/report-evidence.md` (ensayo 2026-11-02) |
| Arquitectura y secuencias | 10 diagramas obligatorios | `docs/architecture/diagrams.md` |
| Decisiones | 9 ADR | `docs/adr/README.md` |

## Reglas de interpretación

- Los resultados de LLM permanecen provisionales porque ninguno supera G1 = 0.80.
- BGE-M3 se compara por recuperación; sus abstenciones se debieron a reutilizar el umbral 0.68 calibrado para Nomic.
- No se afirma revisión humana, validación por especialistas, permiso del corpus, aprobación docente ni ensayo sin conexión.
- Nomic permanece activo por el mejor compromiso entre recuperación, tiempo y tamaño.
