# Registro de decisiones de arquitectura (ADR)

Plantilla de la sección 8 del enunciado: Estado, Contexto, Decisión, Alternativas, Evidencia, Consecuencias. Una decisión cuya evidencia no supera las puertas de `docs/evaluation/acceptance-gates-v1.md` queda **Provisional**.

| ADR | Decisión | Estado |
|---|---|---|
| [ADR-01](ADR-01-fragmentacion-y-metadatos.md) | Fragmentación por página y sección con metadatos de raza controlados | Aceptada |
| [ADR-02](ADR-02-criterio-del-enrutador.md) | Enrutador determinista `simple`/`complex` por complejidad | Aceptada |
| [ADR-03](ADR-03-umbral-cache-semantica.md) | Umbral 0.85 y partición estructural de la caché semántica | Aceptada con riesgo declarado |
| [ADR-04](ADR-04-guardarrailes.md) | Verificaciones de entrada y salida en código | Aceptada |
| [ADR-05](ADR-05-ciclo-de-agente.md) | Ciclo acotado recuperar-evaluar-reformular | Aceptada |
| [ADR-06](ADR-06-persistencia-vectorial.md) | Chroma por generaciones + SQLite como fuente de verdad | Aceptada |
| [ADR-07](ADR-07-seleccion-de-modelos-de-lenguaje.md) | Alias `simple`, `complex` y `fallback` | **Provisional** (G1 no superada) |
| [ADR-08](ADR-08-modelo-de-embeddings.md) | Nomic frente a BGE-M3 | Aceptada (comparación completada el 2026-11-06; BGE-M3 requiere calibración propia) |
| [ADR-09](ADR-09-puntuacion-determinista.md) | Puntuación determinista de BreedMatch | Aceptada |
