# ADR-04: Guardarraíles en código con política por falla

- **Estado:** Aceptada (2026-11-01)

**Contexto.** C3 exige al menos dos verificaciones de entrada y dos de salida, cada una con política (bloquear, reintentar o mensaje seguro). El corpus incluye salud canina histórica que no debe presentarse como consejo actual. Atributos: seguridad, privacidad, apego al contexto.

**Decisión.** Entrada (`InputGuardrailChain`, `guardrails-v1`), en orden: límites de longitud → `input_bounds_invalid`; inyección de instrucciones → `prompt_injection_detected`; datos personales (correo, teléfono) → `sensitive_data_detected`; dominio cinológico (léxico más las palabras distintivas del vocabulario de razas) → `out_of_domain`; criterios de BreedMatch admitidos y válidos. Todas bloquean antes de recuperar o generar.
Salida: esquema estructurado y valores de hallazgo permitidos (`retry`); razas candidatas permitidas y citas resolubles en la evidencia actual (`abstain`); citas obligatorias para hallazgos documentados; encuadre documental en temas de salud (`safety_frame`); en el chat, `verify_answer` convierte citas no resolubles en `unverified` y nunca devuelve el borrador.

**Alternativas.**
- Sólo instrucciones en el prompt: no verificables y vulnerables a inyección.
- Clasificador LLM de seguridad: costo de latencia y no determinista.

**Evidencia.**
- `evaluation/datasets/k9-rubric-v1.json`: 11 entradas problemáticas y 10 normales, etiquetadas antes de medir.
- Primera ejecución (`evaluation/runs/20261102T044739Z-LAYERS-cb245f.json`): detección 1.0, falsos bloqueos 0.10. La entrada normal «Compara el trabajo del beagle y del basset hound» se bloqueaba como `out_of_domain` porque el léxico no incluía esos nombres de raza. Se corrigió derivando el léxico del vocabulario controlado; la ejecución en vivo `evaluation/runs/20261102T050027Z-LAYERS-6fd1ec.json` da detección 1.0, falsos bloqueos 0.0 y exactitud de motivo 1.0. Las etiquetas no se modificaron.
- Pruebas: `backend/tests/test_guardrails.py`, `backend/tests/test_breed_analysis_service.py::test_report_states_which_guardrails_ran`, `backend/tests/test_generation.py`.

**Consecuencias.** Decisiones estables, con código de motivo, visibles en la respuesta (`execution.input_guardrail`, `execution.output_guardrail`) y agregadas en `/admin/metrics`. Riesgo: el léxico de dominio puede bloquear razas fuera del vocabulario si la pregunta no contiene otra palabra del dominio («perro», «raza», «caza»…).
