# ADR-07: Modelos de lenguaje para los alias `simple`, `complex` y `fallback`

- **Estado:** **Provisional** (2026-11-02). Ningún candidato supera la puerta obligatoria G1 y la revisión humana está pendiente.

**Contexto.** R3 y C6 exigen comparar al menos dos modelos locales y enrutar dos de ellos con un criterio explícito. Se dispone de una Mac de 16–18 GB y el corpus está en español.

**Decisión (provisional).**
- `simple` → `llama3.2:3b`.
- `complex` → `qwen3.5:2b`.
- `fallback` → `llama3.2:3b`.
- Todos con `format=json`, `think=false`, tiempo límite de 120 s y un reintento transitorio.

**Alternativas.**
- `llama3.2:3b` en todos los alias: cumple G6 y G7, pero deja C6 sin dos modelos enrutados.
- `qwen3.5:2b` como `simple`: es más rápido (p50 3.7 s frente a 5.1 s) pero falla G6 (falsas abstenciones 0.40) y G7 (0.90).
- Modelos de 7–8 B: no medidos; con dos modelos cargados comprometen la memoria de 16 GB (G18).

**Evidencia** (`docs/evaluation/model-selection-2026-11-02.md`):

| | `llama3.2:3b` | `qwen3.5:2b` |
|---|---:|---:|
| Precisión de cita (G1 ≥ 0.80) | 0.634 ✘ | 0.708 ✘ |
| Salida estructurada (G7) | 1.00 ✔ | 0.90 ✘ |
| Falsas abstenciones (G6) | 0.20 ✔ | 0.40 ✘ |
| p50 / p95 | 5.1 / 8.2 s | 3.7 / 7.8 s |
| Cargado | 3.1 GB | 4.7 GB |
| Licencia | Llama 3.2 Community | Apache 2.0 |

**Consecuencias.**
- En BreedMatch el modelo sólo redacta la síntesis: hallazgos, citas y puntuaciones no dependen de él, y una síntesis con citas no verificables se descarta. Por eso el impacto de G1 en el producto principal es menor que en el chat.
- **No se declara cumplimiento** de R3 ni de la calidad de citas del chat mientras G1 no se supere.
- Siguientes pasos:
  1. revisión humana de las hojas `*.review.csv`;
  2. ampliar `acceptable_pages` del dataset donde la cita adyacente sea legítima, como revisión de datos documentada y no como relajación de la puerta;
  3. probar `complex` = `llama3.2:3b` con otro prompt si G6/G7 de qwen no mejoran.
