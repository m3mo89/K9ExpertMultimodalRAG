# ADR-05: Ciclo acotado recuperar-evaluar-reformular

- **Estado:** Aceptada (2026-11-02). El reformulador es deliberadamente simple; ver riesgos.

**Contexto.** C2 exige al menos un ciclo de agente con máximo de iteraciones. Las consultas cortas o telegráficas («jauría», «lebrel») recuperan con similitud baja y terminaban en abstención.

**Decisión.**
- Tras cada recuperación, `EvidenceSufficiencyPolicy` (similitud máxima ≥ 0.68) decide entre generar y reformular.
- `DomainPreservingReformulator` añade un prefijo de dominio documental y no altera filtros, snapshot ni criterios. Máximo `[agent] max_iterations = 2`.
- Si la última iteración sigue siendo insuficiente, el sistema se abstiene sin llamar al modelo.
- Cada decisión queda en la traza (`agent_decisions`). En BreedMatch la evidencia se acumula entre iteraciones; en el chat se genera con la segunda recuperación.

**Alternativas.**
- Reformulación con LLM: más llamadas de modelo y deriva de la intención sin control.
- Más de dos iteraciones: latencia sin ganancia medida.
- Framework de agentes: dependencia innecesaria para un ciclo acotado.

**Evidencia.**
- `evaluation/runs/20261102T050027Z-LAYERS-6fd1ec.json` (12 casos): terminación 1.0; 6/12 reformulan y 6/6 de ellos generan tras reformular.
- Primera ejecución en vivo (`20261102T045732Z-LAYERS-3c58a6`): en BreedMatch, la segunda iteración sustituía la evidencia y perdía hallazgos (BM2). Se corrigió acumulando evidencia (`backend/tests/test_breed_analysis_service.py::test_reformulation_adds_evidence_instead_of_replacing_it`).
- Pruebas: `backend/tests/test_orchestrator.py::test_agent_reformulates_once_then_generates_or_terminates`, `backend/tests/test_breed_analysis_service.py::test_agent_*`.

**Consecuencias.** El ciclo es determinista, acotado y visible en la traza y en `execution.agent_iterations`. **Riesgos medidos:**
1. El prefijo de dominio eleva la similitud de casi cualquier consulta (p. ej. «trufa negra» de 0.631 a 0.681), así que «mejorar tras reformular» refleja en parte una inflación de similitud y no necesariamente mejor evidencia. La verificación de citas sigue siendo la barrera real.
2. Las preguntas fuera de alcance pero con vocabulario canino (A5, A6) superan la suficiencia en la primera iteración: decisión final 0.67 en los casos etiquetados originalmente (G13, no obligatoria, no se cumple).
