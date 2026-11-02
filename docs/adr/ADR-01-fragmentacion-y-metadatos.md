# ADR-01: Fragmentación por página y sección con metadatos de raza

- **Estado:** Aceptada (2026-11-01)

**Contexto.** La enciclopedia (243 páginas, 1 PDF) organiza cada raza en apartados fijos («Cabeza», «Cuerpo», «Cola», «Manto», «El trabajo y las cualidades»). BreedMatch necesita evidencia por raza y criterio con su página física, y las citas deben resolverse a una página exacta. Atributo de calidad: precisión de recuperación y trazabilidad de citas.

**Decisión.** Fragmentar por página y por sección tipográfica (`page-section-v3-classified`, ~109 palabras por fragmento, sin cruzar páginas). Cada fragmento lleva la ruta de sección y, cuando la estructura lo establece sin ambigüedad, metadatos normalizados de raza, grupo, función de caza y apartado según el vocabulario controlado `k9-reference-v1`. Los valores dudosos quedan vacíos.

**Alternativas.**
- Ventanas fijas de 500–1000 caracteres con solapamiento: mezclan razas en un mismo fragmento y rompen la cita por página.
- Clasificación por LLM en la ingesta: no reproducible y sin procedencia auditable.
- Fragmentación por raza completa: fragmentos demasiado largos para la ventana de contexto de 8192 tokens.

**Evidencia.**
- Ingesta en staging del 2026-11-02 (registro de `scripts/stage_reference_corpus.py`): 243 páginas, 786 fragmentos, 438 clasificados, 227 páginas de texto directo y 16 que requerirían OCR.
- `docs/evaluation/baseline-2026-11-01.md`: la versión 1 producía 798 fragmentos de menos de 80 caracteres; la versión 2 corrigió las secciones espurias.
- Pruebas: `backend/tests/test_breed_vocabulary.py`, `backend/tests/test_extraction.py`, `backend/tests/test_vector_index.py::test_generation_index_keeps_candidate_metadata_and_filters`.
- E2 de referencia: Recall@5 = 0.81 con este esquema (`evaluation/runs/20261101T235315Z-E2-ce2fd4.json`).

**Consecuencias.** Se gana filtrado por raza y citas a página exacta. Se sacrifica cobertura: 348 fragmentos sin raza no entran en los filtros por raza (preferimos omitir a clasificar mal). Riesgo: un título no detectado (p. 236, «espiga en el oído» bajo «Fracturas») asigna una sección incorrecta; queda documentado.
