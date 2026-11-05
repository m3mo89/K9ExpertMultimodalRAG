# Baseline automatizado de recomendación — 2026-11-04

> **Nota posterior.** Este registro es anterior a `automate-breed-knowledge-publication`. Desde ese
> cambio, las afirmaciones extraídas por reglas que superan la validación se publican sin revisión
> humana; lo extraído por el modelo sigue sin publicarse sin aprobación explícita, que es lo que
> cubre la fila «Ingesta adversarial». Los conteos de pruebas corresponden a la fecha de este
> registro y no se han actualizado. La limitación de liberación sigue vigente.

## Gates ejecutados

| Gate | Resultado |
|---|---|
| Repetición de perfiles fijos y orden determinista | Aprobado por `test_recommendation.py` y `test_recommendation_api.py` |
| Degradación sin Ollama | Aprobado: resultados y citas continúan; narrativa queda indisponible |
| Ingesta adversarial | Aprobado: JSON inválido, IDs inventados y texto con instrucciones se descartan; no se autopublican afirmaciones |
| Integridad de snapshots/rollback | Aprobado por pruebas de publicación y conocimiento estructurado |
| Backend | 171 pruebas aprobadas |
| Frontend | 37 pruebas aprobadas; build correcto |
| Lint/tipos | Ruff y mypy correctos; oxlint informa tres advertencias React no bloqueantes preexistentes |

## Limitación de liberación

El dataset `k9-recommendation-v1` contiene por ahora sólo el caso de abstención/información
incompleta y no contiene juicios de especialistas ni afirmaciones de raza aprobadas por humanos.
Por ello no se ha ejecutado ni se afirma un gate de acuerdo experto, nDCG humano o evaluación de
adecuación de raza. El flujo guiado no debe declararse validado por especialistas ni habilitarse
como recomendación de producción hasta que se incorporen revisiones independientes con procedencia.
