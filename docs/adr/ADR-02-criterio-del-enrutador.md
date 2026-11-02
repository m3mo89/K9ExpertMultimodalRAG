# ADR-02: Enrutador determinista por complejidad

- **Estado:** Aceptada (2026-11-01). Los modelos concretos detrás de cada alias se deciden en ADR-07.

**Contexto.** C6 exige al menos dos modelos de lenguaje enrutados con un criterio explícito. Las consultas varían entre una raza y un criterio (síntesis corta) y comparaciones de varias razas, muchos criterios o evidencia abundante. Atributos: latencia en el caso común, calidad en el caso complejo, auditabilidad.

**Decisión.** `ComplexityRouter` (`router-v1`) elige `complex` si se cumple la primera de estas reglas, en orden: hubo reformulación del agente; más de 2 candidatos; más de 3 criterios; más de 6 fragmentos de evidencia. En otro caso, `simple` con motivo `bounded_request`. Las capas superiores sólo ven alias; el gateway resuelve el modelo concreto, aplica tiempo límite, reintento acotado y respaldo local `fallback`.

**Alternativas.**
- Clasificador por LLM: añade una llamada de modelo y no es reproducible.
- Enrutamiento por intención con palabras clave: frágil frente a nombres de raza abiertos.
- Un solo modelo: incumple C6.

**Evidencia.**
- Dataset etiquetado `evaluation/datasets/k9-rubric-v1.json` (sección `router`, 8 casos): exactitud 1.0 en `evaluation/runs/20261102T050027Z-LAYERS-6fd1ec.json`.
- Pruebas: `backend/tests/test_routing.py` (cada regla y motivo; respaldo local y ausencia de alias externo), `backend/tests/test_orchestrator.py::test_grounded_query_routes_through_logical_aliases_and_traces_fallback`.

**Consecuencias.** Decisión explicable y trazada (`route`, `route_reason`, `resolved_model`, `fallback_used`). Los umbrales (2, 3, 6) son de diseño, no calibrados: deben revisarse con la latencia por ruta medida en ADR-07.
