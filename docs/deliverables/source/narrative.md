# Narrativa común

## Título

K9 BreedMatch: arquitectura local en capas para la recomendación explicable de razas de perros de caza mediante embeddings y RAG.

## Tesis

K9 BreedMatch no es un chatbot: transforma un perfil de caza —presa, modalidad de trabajo y terreno— en una recomendación estructurada con compatibilidad determinista, cobertura de evidencia y citas verificables.

## Metadatos editables

- Alumno: `[NOMBRE DEL ALUMNO]`
- Institución: `[INSTITUCIÓN]`
- Asignatura: `Tópicos selectos de arquitectura de software · Unidad II`
- Docente: `[NOMBRE DEL DOCENTE]`
- Fecha: `7 de noviembre de 2026`

## Decisión de modelos

- LLM simple y respaldo: `llama3.2:3b`; mejor salida estructurada y menos falsas abstenciones.
- LLM complejo: `qwen3.5:2b`; menor latencia y mayor precisión de cita, con estado provisional.
- Embeddings activos: `nomic-embed-text`; empata Recall@5 e Hit@5 con BGE-M3, pero es más pequeño y rápido.
- Segundo candidato: `bge-m3`; mejora Recall@1 y MRR ligeramente, sin justificar el costo para este corpus.

## Mensaje de cierre

El valor del sistema no está en generar texto libre, sino en producir una decisión auditable: qué raza se recomienda, con qué cobertura, por qué y en qué página se sustenta.
