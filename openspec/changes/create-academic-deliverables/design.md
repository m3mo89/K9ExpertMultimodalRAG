## Context

El enunciado exige una presentación con demostración local y un informe técnico de 15 a 25 páginas. El repositorio ya contiene la implementación, diez diagramas Mermaid, nueve ADR, matrices de trazabilidad y ejecuciones de evaluación. Los entregables deben sintetizar esas fuentes sin duplicar inconsistencias ni convertir pendientes en afirmaciones de cumplimiento.

Los lectores son el docente y evaluadores académicos. La presentación debe priorizar legibilidad y narrativa oral; el informe debe priorizar evidencia, decisiones y reproducibilidad. Ambos deben poder editarse y exportarse con herramientas comunes.

## Goals / Non-Goals

**Goals:**

- Producir un `.pptx` de aproximadamente 12 diapositivas, adecuado para 15 minutos de exposición y cinco minutos de demostración.
- Producir un `.docx` de 15 a 25 páginas, con estilos, numeración, tablas, figuras, referencias y anexos.
- Reutilizar una narrativa y un conjunto de cifras comunes para evitar contradicciones entre documentos.
- Generar recursos visuales legibles a partir de los diagramas existentes.
- Verificar estructura, contenido, integridad de archivos y fidelidad de cifras antes de entregar.

**Non-Goals:**

- Modificar el backend, frontend, corpus, modelos activos o API.
- Corregir resultados experimentales que no superaron las puertas de aceptación.
- Inventar revisiones humanas, validaciones expertas, permisos o aprobaciones docentes.
- Sustituir la demostración local obligatoria por las diapositivas.

## Decisions

1. **Una fuente narrativa intermedia.** Se preparará contenido estructurado común para portada, propuesta de valor, arquitectura, selección de modelos, evaluación y limitaciones. Alternativa: redactar cada archivo por separado. Se descarta porque favorece inconsistencias.

2. **PowerPoint visual y temporizado.** La presentación tendrá alrededor de 12 diapositivas, poco texto, notas del presentador y una secuencia de demostración. Alternativa: trasladar el informe a diapositivas. Se descarta por legibilidad y manejo del tiempo.

3. **Word académico editable.** El informe se generará como `.docx` con estilos jerárquicos, pies de figura, tablas y referencias. Alternativa: entregar solo Markdown o PDF. Se descarta porque el usuario solicitó Word y necesita una fuente editable.

4. **Diagramas derivados de la fuente versionada.** Se renderizarán los diagramas de `docs/architecture/diagrams.md` y se reutilizarán en ambos entregables. Alternativa: redibujarlos manualmente. Se descarta por riesgo de divergencia arquitectónica.

5. **Dos niveles de evidencia.** Las cifras principales aparecerán en el cuerpo; identificadores de ejecuciones, detalles de ADR y tablas extensas quedarán en notas o anexos. Esto mantiene la presentación clara sin perder auditabilidad.

6. **Limitaciones visibles.** Las decisiones provisionales y pendientes se etiquetarán expresamente. La comparación de embeddings conservará Nomic como seleccionado y BGE-M3 como candidato evaluado; no se reinterpretará la abstención de BGE-M3 como fallo de recuperación.

7. **Marcadores para metadatos desconocidos.** Nombre del alumno, institución, docente y logotipo quedarán como campos editables si no se proporcionan durante la implementación.

## Risks / Trade-offs

- **[Diagramas demasiado densos]** → Crear variantes simplificadas para las diapositivas y conservar las completas en el informe.
- **[Paginación diferente entre Word y PDF]** → Validar el `.docx` y una exportación PDF de control; ajustar saltos y tamaños sin exceder 25 páginas de cuerpo.
- **[Cifras contradictorias entre ejecuciones]** → Usar la matriz de evidencia y citar el identificador exacto de cada corrida.
- **[Afirmaciones académicas no verificadas]** → Etiquetar revisión humana, permiso del corpus, aprobación docente y validación experta como pendientes.
- **[Dependencias de generación no disponibles]** → Detectar primero las herramientas instaladas y elegir generación reproducible con dependencias locales mínimas.
- **[Demostración excede cinco minutos]** → Preparar una ruta principal ensayada y un plan B con capturas o video, sin sustituir la demostración evaluada.
