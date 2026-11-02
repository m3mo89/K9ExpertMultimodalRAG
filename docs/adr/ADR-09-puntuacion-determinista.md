# ADR-09: Puntuación determinista de BreedMatch

- **Estado:** Aceptada (2026-11-01). Los pesos por defecto (1, editable 1–10) son de diseño; se revisan con la retroalimentación.

**Contexto.** R12 exige un producto que entregue un resultado, no un chat. Un recomendador sólo-LLM no es reproducible ni auditable, y el corpus no documenta todos los rasgos de todas las razas. Atributos: transparencia, reproducibilidad, no inventar datos.

**Decisión.** `DeterministicBreedMatcher` (`breed-match-v1`): por raza y criterio, `match` si la evidencia recuperada contiene el valor normalizado sin negación cercana; `mismatch` si aparece negado («no», «nunca», «sin» a ≤ 35 caracteres); `not_documented` en otro caso. Puntuación = peso coincidente ÷ peso documentado; cobertura = peso documentado ÷ peso posible; sin puntuación si la cobertura es menor que `minimum_coverage = 0.5`. El modelo sólo redacta una síntesis sobre los hallazgos verificados y sus citas.

**Alternativas.**
- Puntuación por LLM: opaca y no reproducible.
- Similitud media de embeddings como puntuación: no explica qué criterio coincide.

**Evidencia.**
- Pruebas: `backend/tests/test_breed_match.py` (hallazgos con citas, puntuación omitida bajo cobertura, orden reproducible, negación como `mismatch`), `backend/tests/test_breed_analysis_service.py`.
- Casos BM1–BM5 de `evaluation/datasets/k9-rubric-v1.json`, verificados con el texto de las páginas (p. ej. p. 165: «sin flecos ondulados» → `mismatch` para el labrador).

**Consecuencias.** Cada puntuación se explica con sus términos en la interfaz. Limitación conocida: la coincidencia es por subcadena (p. ej. «muestra» coincide con el verbo «se muestra»), por eso los casos de evaluación evitan ese término y la limitación se declara en el informe.
