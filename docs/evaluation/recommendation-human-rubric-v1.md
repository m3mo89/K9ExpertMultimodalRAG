# Rúbrica humana de recomendaciones v1

Cada perfil debe ser revisado independientemente por al menos dos especialistas. Para cada caso se registra: candidatos aceptables ordenados o empatados, razones por dimensión, restricciones duras, evidencia/páginas esperadas, abstención requerida y nivel de confianza.

El acuerdo se reporta por top-k, dimensión y decisión de abstención. Los desacuerdos no se convierten en una única etiqueta: se preservan las respuestas individuales, la discusión de conciliación y el estado `unresolved` cuando corresponda. Ningún modelo de generación o narrativa puede ser el único evaluador de adecuación o fidelidad.

## Plantilla de revisión

| Campo | Registro requerido |
|---|---|
| Revisor y fecha | Identidad o seudónimo estable, fecha, conflicto de interés |
| Perfil | Versión y respuestas normalizadas |
| Candidatos | Orden, empates y candidatos no recomendables |
| Dimensiones | Coincide / contradice / desconocido con fundamento |
| Evidencia | Documento, edición, página y fragmento |
| Abstención | Requerida/no requerida y motivo |
| Desacuerdo | Aceptable, conciliado o no resuelto |
