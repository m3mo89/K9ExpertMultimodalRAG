## ADDED Requirements

### Requirement: Estructura obligatoria del informe
El informe técnico SHALL cubrir los doce apartados de la sección 11.1 del enunciado y mantener una extensión sugerida de 15 a 25 páginas para el cuerpo principal.

#### Scenario: Revisión de cobertura
- **WHEN** se compara el índice del informe con el enunciado
- **THEN** aparecen portada y resumen, idea, dominio, requisitos, arquitectura, comportamiento, modelos, capas, ADR, evaluación, limitaciones, referencias y anexos

### Requirement: Diagramas obligatorios
El informe MUST incluir las cinco vistas estructurales y las cinco secuencias obligatorias con número, título y explicación.

#### Scenario: Revisión de figuras
- **WHEN** el evaluador inspecciona las figuras del informe
- **THEN** encuentra contexto, contenedores, capas, componentes, despliegue, ingesta, consulta normal, caché, bloqueo y ciclo de agente

### Requirement: Decisiones de arquitectura
El informe SHALL resumir al menos seis ADR con contexto, decisión, alternativas, evidencia y consecuencias, manteniendo coherencia con `docs/adr/`.

#### Scenario: Auditoría de ADR
- **WHEN** se contrasta una decisión del informe con su ADR fuente
- **THEN** el estado, la evidencia y las consecuencias no se contradicen

### Requirement: Evaluación y análisis honesto
El informe SHALL presentar recuperación, generación, guardrails, caché, router, agente, latencia y recursos, diferenciando resultados medidos de pendientes.

#### Scenario: Resultado no aprobado
- **WHEN** una métrica no alcanza su puerta de aceptación
- **THEN** el informe la identifica como limitación y no declara cumplimiento total

### Requirement: Documento Word editable
El informe MUST entregarse como un `.docx` válido con estilos de título, tablas, figuras, numeración de página y campos editables de portada.

#### Scenario: Apertura del documento
- **WHEN** el archivo se abre con una aplicación compatible con Word
- **THEN** conserva su jerarquía, tablas, imágenes y contenido sin advertencias de corrupción

