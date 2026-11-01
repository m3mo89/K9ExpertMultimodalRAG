## Why

La información cinológica disponible en documentos PDF es difícil de consultar, comparar y actualizar de forma verificable. K9 Expert necesita un primer producto local que convierta una biblioteca de múltiples PDF en respuestas fundamentadas, con citas por página, abstención cuando no exista respaldo y gestión segura de versiones documentales, antes de incorporar análisis de fotografías.

## What Changes

- Crear una aplicación web responsiva y un backend local desacoplado para consultas textuales sobre una biblioteca cinológica.
- Incorporar múltiples PDF mediante extracción directa de texto, OCR selectivo, fragmentación estructurada e indexación incremental.
- Gestionar documentos y versiones con publicación atómica, de modo que una actualización fallida no sustituya la versión activa.
- Recuperar evidencia mediante búsqueda semántica y filtros por fuente y metadatos, preservando contratos que permitan añadir recuperación léxica/híbrida posteriormente.
- Generar respuestas con atribución de fuente, edición y página, mostrando contradicciones y absteniéndose ante evidencia insuficiente.
- Permitir consultar, activar, desactivar, reemplazar, reindexar y eliminar fuentes mediante operaciones administrativas protegidas y confirmación de acciones destructivas.
- Mantener conversaciones, historial y retroalimentación básica sobre la utilidad de las respuestas.
- Registrar trazas de consultas e ingestas y proporcionar un conjunto de evaluación reproducible para recuperación, fidelidad, citas, abstención y latencia.
- Ejecutar inferencia y almacenamiento localmente, sin APIs comerciales ni exposición directa de Ollama o del índice vectorial al frontend.
- Excluir del MVP el análisis de fotografías, la identificación de razas, la recuperación de imágenes, los embeddings multimodales, la PWA, la caché semántica y un sistema multiusuario avanzado.

## Capabilities

### New Capabilities

- `document-library`: Registro, navegación, estado y administración segura del ciclo de vida de documentos y versiones.
- `document-ingestion`: Validación, extracción, OCR selectivo, fragmentación, embeddings e indexación incremental mediante trabajos persistentes.
- `atomic-index-publication`: Construcción, validación y publicación atómica de snapshots, con conservación de la versión previa ante fallos.
- `grounded-query`: Consultas textuales con filtros, recuperación de evidencia, generación local, abstención y tratamiento explícito de discrepancias.
- `verifiable-citations`: Citas comprobables que identifican documento, versión, edición, página y fragmento de evidencia.
- `conversation-feedback`: Historial de conversaciones y retroalimentación asociada a respuestas.
- `local-administration`: Protección de mutaciones administrativas, confirmación de operaciones destructivas y diagnóstico de servicios locales.
- `ai-observability-evaluation`: Trazas estructuradas, métricas operativas y evaluación reproducible del sistema RAG.

### Modified Capabilities

No existen especificaciones principales previas que deban modificarse.

## Impact

- Se crearán frontend web, API backend, trabajador local de ingesta y módulos de dominio, aplicación e infraestructura.
- Se definirán contratos REST versionados para consultas, documentos, trabajos, citas, conversaciones, retroalimentación, salud y métricas.
- Se introducirán almacenamiento relacional local, almacenamiento de archivos e índice vectorial derivado; el modelo relacional será la autoridad de publicación.
- Se integrarán runtime de inferencia local, extracción PDF, OCR selectivo y generación de embeddings mediante adaptadores reemplazables.
- La implementación deberá funcionar en una Mac Apple Silicon con 16 GB, usando concurrencia y carga de modelos conservadoras, sujetas a benchmarks.
- Los dos PDF existentes servirán como fuentes iniciales y material arquitectónico, sin asumir que todo su contenido sea vigente o exhaustivo.
