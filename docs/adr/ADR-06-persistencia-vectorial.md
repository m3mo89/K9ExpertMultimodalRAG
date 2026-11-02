# ADR-06: Chroma por generaciones y SQLite como fuente de verdad

- **Estado:** Aceptada (2026-11-01)

**Contexto.** Hay que guardar vectores, metadatos, versiones de documentos, cachés, trazas, retroalimentación y análisis en local, con publicación atómica y vuelta atrás. C7 exige que cambiar la base vectorial no obligue a modificar las capas superiores.

**Decisión.** Chroma persistente embebido, con una colección por generación de índice (snapshot). SQLite guarda documentos, versiones, pertenencia de fragmentos a cada snapshot, cachés exacta y semántica, trazas, retroalimentación y análisis de BreedMatch; es la fuente de verdad. La recuperación pasa por `SnapshotRetriever` (puerto de C5); sólo `ChromaGenerationIndex` conoce Chroma. Cada snapshot registra la identidad de embeddings (alias, modelo, dimensión); publicar con otra identidad exige reindexación completa.

**Alternativas.**
- FAISS: sin metadatos ni filtros nativos; más código propio.
- Qdrant o pgvector: un servidor adicional en la Mac de entrega.
- Mutar la colección activa: rompe la consistencia de snapshot y la vuelta atrás.
- Redis para la caché: infraestructura innecesaria; SQLite basta para el volumen local.

**Evidencia.**
- Pruebas: `backend/tests/test_snapshots.py::test_snapshot_activation_rollback_and_invalidation_are_atomic`, `backend/tests/test_pipeline.py::test_deactivation_deletion_history_and_rollback`, `backend/tests/test_vector_index.py`, `backend/tests/test_breed_analysis_persistence.py` (migración aditiva, copia y restauración de tablas nuevas).
- Staging del corpus: 786 vectores de 768 dimensiones publicados en una generación nueva en 25.8 s.

**Consecuencias.** Publicación atómica y vuelta atrás sin reconstruir. Se sacrifica espacio en disco (generaciones antiguas) hasta la limpieza. La búsqueda semántica de la caché es lineal sobre su partición en SQLite: suficiente para el volumen de una demostración local, no para miles de entradas.
