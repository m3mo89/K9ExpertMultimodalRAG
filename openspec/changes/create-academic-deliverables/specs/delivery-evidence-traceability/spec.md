## ADDED Requirements

### Requirement: Fuente para cada cifra
Cada cifra experimental incluida en los entregables MUST poder rastrearse a un archivo de evaluación, ADR o documento de evidencia versionado.

#### Scenario: Auditoría de una métrica
- **WHEN** se selecciona una cifra de modelos, recuperación, caché o guardrails
- **THEN** existe una referencia que permite localizar su ejecución o documento fuente

### Requirement: Consistencia entre entregables
La presentación y el informe SHALL usar los mismos nombres de producto, arquitectura, modelos activos, métricas y estados de cumplimiento.

#### Scenario: Comparación cruzada
- **WHEN** una afirmación aparece en ambos entregables
- **THEN** sus valores, alcance y calificación como medida, provisional o pendiente coinciden

### Requirement: Evidencia incompleta identificada
Los entregables MUST identificar como pendientes la revisión humana, la validación por especialistas, el permiso de uso del corpus, la aprobación docente y el ensayo sin conexión cuando no exista evidencia de cierre.

#### Scenario: Ausencia de evidencia
- **WHEN** no existe un artefacto que demuestre el cierre de un pendiente
- **THEN** el texto usa una formulación explícita de limitación y no una afirmación de cumplimiento

### Requirement: Validación de los archivos finales
Los entregables MUST someterse a comprobaciones de integridad estructural, contenido requerido y renderizado visual antes de considerarse completos.

#### Scenario: Verificación final
- **WHEN** termina la generación de `.pptx` y `.docx`
- **THEN** ambos archivos abren correctamente, incluyen las secciones requeridas y sus vistas renderizadas no presentan recortes ni desbordamientos importantes

