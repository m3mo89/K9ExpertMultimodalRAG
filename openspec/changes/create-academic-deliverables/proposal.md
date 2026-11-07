## Why

K9 BreedMatch ya cuenta con implementación, diagramas, ADR y evidencia experimental, pero la entrega académica obligatoria aún no existe como presentación ni como informe técnico final. Es necesario convertir la evidencia versionada en dos documentos coherentes, verificables y alineados con `Proyecto_integrador_RAG.pdf` sin presentar resultados pendientes como concluyentes.

## What Changes

- Crear una presentación PowerPoint para una exposición de 15 minutos, con apoyo visual, notas del presentador y un guion de demostración local de cinco minutos.
- Crear un informe técnico Word de 15 a 25 páginas, preparado para exportarse a PDF y organizado según la sección 11 del enunciado.
- Incorporar los diagramas obligatorios de contexto, contenedores, capas, componentes, despliegue y secuencias como recursos visuales legibles.
- Presentar la comparación medida de `llama3.2:3b` y `qwen3.5:2b`, y de `nomic-embed-text` y `bge-m3`, explicando los criterios y la decisión adoptada.
- Mantener trazabilidad entre afirmaciones, tablas, gráficas y sus fuentes versionadas en el repositorio.
- Distinguir resultados medidos, decisiones provisionales y limitaciones pendientes, incluyendo precisión de citas, revisión humana, validación experta y ensayo sin conexión.
- Usar marcadores editables para los datos académicos que el usuario todavía no ha proporcionado.

## Capabilities

### New Capabilities

- `academic-presentation`: Presentación visual, temporizada y respaldada por evidencia para exponer la propuesta de valor, arquitectura, selección de modelos, demostración y resultados.
- `technical-report`: Informe técnico académico con arquitectura, comportamiento, ADR, evaluación, limitaciones, referencias y anexos reproducibles.
- `delivery-evidence-traceability`: Trazabilidad de las cifras y afirmaciones de ambos entregables hacia ADR, diagramas, ejecuciones de evaluación y documentación del repositorio.

### Modified Capabilities

Ninguna. El cambio produce entregables académicos y no modifica el comportamiento del producto ni sus API.

## Impact

Se añadirán archivos de presentación, informe y recursos visuales bajo `docs/deliverables/`. Se reutilizarán `docs/architecture/diagrams.md`, `docs/adr/`, `docs/evaluation/`, `docs/rubric/`, `evaluation/runs/`, `README.md` y el enunciado de referencia. No se modificarán el backend, frontend, modelos activos, datos operacionales ni contratos de API. La generación puede requerir bibliotecas locales para producir `.pptx`, `.docx`, imágenes y PDF de verificación.
