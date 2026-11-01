# Conjunto de referencia de recuperación v1

## Propósito y alcance

Este conjunto permite medir recuperación textual del PDF `Enciclopedia de los perros de caza`, Claudio De Giuliani, Editorial De Vecchi, 2019, ISBN 978-1-68325-599-4. Cada página indicada es la página física del PDF de 243 páginas, no la numeración impresa del libro.

Los casos se verificaron mediante extracción directa de texto con PDFKit el 2026-11-01. Son casos de recuperación: la respuesta de generación debe mantenerse atribuida a la fuente, no sustituye evaluación profesional, veterinaria ni de estándares vigentes.

## Convenciones

- `expected_pages`: al menos una de estas páginas debe aparecer entre los resultados relevantes.
- `required_terms`: expresiones o conceptos que el evaluador humano espera en una respuesta fiel; no son una clave de coincidencia literal.
- `expected_state`: `grounded`, `abstain` o `filtered-abstain`.
- `source_filter`: filtro que debe respetarse sin ampliar la búsqueda implícitamente.

## Casos

| ID | Clase | Pregunta | expected_pages | required_terms | expected_state | source_filter |
|---|---|---|---|---|---|---|
| R1 | explícita/morfología | ¿Cómo describe el libro la cabeza y el cuerpo del teckel alemán? | 27 | cráneo ligeramente convexo; stop poco visible; tronco alargado; esternón cerca del suelo | grounded | Enciclopedia activa |
| R2 | explícita/trabajo | Según la enciclopedia, ¿qué cualidades y trabajos se atribuyen al teckel alemán? | 27, 28 | tenacidad; obstinación; coraje; cubil; acoso | grounded | Enciclopedia activa |
| R3 | explícita/morfología | ¿Qué rasgos de cola y manto documenta el libro para el norsk elghund? | 29 | cola enroscada sobre el lomo; pelo denso; abundante; áspero | grounded | Enciclopedia activa |
| R4 | comparación | Compara la constitución descrita para el beagle y el basset hound. | 104, 106 | beagle proporcionado/armonioso; basset de 33 a 38 cm; diferencias atribuidas a cada raza | grounded | Enciclopedia activa |
| R5 | comparación/trabajo | ¿Cómo contrasta el libro el trabajo del beagle con el del basset hound? | 105, 107 | beagle: conejo/liebre, rápido y resistente; basset: liebre/conejo, pieza herida | grounded | Enciclopedia activa |
| R6 | explícita/historia | ¿Qué afirma el autor sobre la historia y el uso del norsk elghund? | 29, 30 | taiga/Gran Norte; alce; hocico al aire; voz al avistarlo | grounded | Enciclopedia activa |
| R7 | seguridad/documental | ¿Qué indica esta fuente ante síntomas de enfermedad? | 226 | llevar al veterinario; información atribuida al libro; sin diagnóstico individual | grounded | Enciclopedia activa |
| R8 | seguridad/documental | ¿Qué afirma el libro sobre una espiga dentro del oído? | 236 | inmovilizar; llevar al veterinario; no sustituye atención profesional | grounded | Enciclopedia activa |
| R9 | abstención | ¿Cuál es la dosis de ibuprofeno para mi perro? | — | no debe inventar dosis ni diagnóstico | abstain | Enciclopedia activa |
| R10 | abstención/filtro | Con la categoría de raza `Terrier` como único filtro, ¿qué dice la fuente sobre la cola del norsk elghund? | 29 fuera del filtro | no ampliar a otra categoría; informar falta de respaldo en el alcance seleccionado | filtered-abstain | categoría=Terrier |

## Criterios de revisión humana

1. La evidencia recuperada pertenece a la versión activa y al filtro solicitado.
2. La respuesta no usa una página de índice como única evidencia material.
3. Una respuesta `grounded` contiene por lo menos una cita página-fragmento resoluble.
4. Las comparaciones atribuyen cada rasgo a la raza correspondiente y muestran “No documentado” si un atributo no figura en la evidencia.
5. Los casos R7, R8 y R9 no se califican como correctos si ofrecen consejo veterinario concluyente o una dosis.
6. R10 sólo es correcto si no ensancha silenciosamente el filtro de categoría.

## Límites conocidos

- Este conjunto es intencionadamente pequeño; no sustituye un conjunto retenido ni una revisión independiente.
- Las etiquetas de categoría y raza todavía deberán provenir del pipeline de estructura documental. Antes de eso, R10 puede ejecutarse contra metadatos de prueba explícitos.
- Las páginas verificadas contienen contenido histórico/documental; su presencia no acredita vigencia clínica o normativa.
