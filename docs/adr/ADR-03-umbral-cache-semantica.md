# ADR-03: Umbral y partición de la caché semántica

- **Estado:** Aceptada con riesgo declarado (2026-11-02). Se revisa al ampliar los pares de evaluación.

**Contexto.** C4 exige caché exacta y semántica, con umbral justificado, expiración e invalidación cuando cambian los documentos. En BreedMatch, servir un informe de otro perfil sería un error de producto, no sólo de rendimiento.

**Decisión.**
- Cachés persistentes en SQLite, ligadas al snapshot activo, con TTL de 3600 s (exacta) y 1800 s (semántica).
- La partición fija la operación, la identidad (políticas y modelos), las claves y pesos de los criterios, las razas candidatas y los documentos. La búsqueda semántica sólo compara la redacción de los criterios dentro de esa partición.
- Un acierto se rechaza si cambian las funciones de caza controladas (rastro, muestra, cobro, busca, terrier, agua).
- La salida en caché se revalida con los guardarraíles de salida antes de devolverla.
- Umbral semántico: **0.85**, obtenido con la regla prerregistrada.

**Alternativas.**
- 0.92 (valor inicial): no reutilizaba C3 («pelo duro» frente a «pelo áspero y duro», 0.911).
- Sin partición estructural: la similitud de embeddings no distingue pesos ni razas (C6 y C8 tienen similitud 1.0 y deben separarse).
- Redis o memoria: no persisten entre reinicios ni se invalidan por snapshot.

**Evidencia.**
- `evaluation/runs/20261102T045930Z-CALIBRATION-bb4123.json`: en desarrollo, los pares «separate» de la misma partición dan 0.752 (C5) y 0.695 (C9); la regla aplica el mínimo 0.85. En retenidos: 0 reutilizaciones indebidas y 1/1 paráfrasis reutilizada.
- `evaluation/runs/20261102T050027Z-LAYERS-6fd1ec.json`: exacta 1.0, paráfrasis 2/2, separación 6/6, 0 violaciones (G10).
- Pruebas: `backend/tests/test_breed_analysis_service.py` (exacta, semántica y separación por función), `backend/tests/test_breed_analysis_persistence.py::test_exact_semantic_partition_and_snapshot_invalidation`.

**Consecuencias.** Las paráfrasis cercanas se sirven sin recuperar ni generar, y el sistema traza la similitud y el umbral. **Riesgo:** C10 («pelo corto» frente a «pelo largo», contradictorios) tiene similitud 0.828, a 0.022 del umbral; con 10 pares la estimación es frágil. Mitigaciones: partición estructural, comprobación de funciones, TTL corto y revalidación. Trabajo futuro: comprobar antónimos de rasgos controlados (corto/largo, liso/duro) como se hace con las funciones.
