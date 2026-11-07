## ADDED Requirements

### Requirement: Presentación alineada con la exposición
La presentación SHALL organizar la idea, arquitectura, selección de modelos, demostración, evaluación y limitaciones para una exposición de aproximadamente 15 minutos.

#### Scenario: Recorrido completo de la presentación
- **WHEN** el estudiante expone las diapositivas en orden
- **THEN** la narrativa cubre la idea en 2 minutos, arquitectura en 3, modelos y RAG en 3, demostración en 5 y resultados y limitaciones en 2

### Requirement: Contenido visual y legible
La presentación MUST priorizar diagramas, tablas y cifras clave sobre párrafos, con texto legible en una pantalla de proyección.

#### Scenario: Revisión visual
- **WHEN** las diapositivas se renderizan como imágenes o PDF
- **THEN** no existen elementos recortados, texto desbordado ni tablas ilegibles a tamaño normal

### Requirement: Selección de modelos explicada
La presentación SHALL mostrar los dos modelos de lenguaje y los dos modelos de embeddings evaluados, los criterios medidos y la justificación de la selección activa.

#### Scenario: Comparación de modelos
- **WHEN** el evaluador revisa la sección de modelos
- **THEN** puede identificar candidatos, métricas, recursos, decisión y carácter provisional de los resultados que no superan sus puertas

### Requirement: Guion de demostración
La presentación MUST incluir notas del presentador con una demostración de carga o estado, recomendación con fuentes, caché, guardrail, ciclo de agente, retroalimentación, métricas y OpenAPI.

#### Scenario: Ensayo de demostración
- **WHEN** el estudiante sigue las notas del presentador
- **THEN** dispone de una secuencia principal de cinco minutos y una indicación de plan B ante fallos locales

