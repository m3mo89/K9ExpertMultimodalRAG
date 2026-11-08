# K9 BreedMatch — matriz de cumplimiento

**Versión auditada:** `ec5fe0bf5fce63067175816d05697643de3f1e6f` (2026-11-07).  
**Estados:** Cumple = implementación y evidencia suficientes; Parcial = existe implementación con una brecha medida; Pendiente = no existe evidencia concluyente; No aplica = fuera del producto evaluado.

| Criterio | Evidencia verificable | Sección del informe | Estado | Pendiente o brecha |
|---|---|---:|---|---|
| R1 (*) Dominio y corpus | `README.md`; `evaluation/datasets/k9-reference-v2.json`; PDF de 243 páginas; corrida Nomic con 786 fragmentos | 2, 3 | Cumple con reserva | Confirmar por escrito el permiso de uso académico; el corpus es un solo documento, aunque supera 50 páginas. |
| R2 (*) Ejecución local | `config/k9.defaults.toml`; `RoutedOllamaGateway`; `scripts/preflight.py`; puertos 5173/8000/11434 | 5, 11 | Parcial | No se conserva evidencia de un ensayo integral sin red en la Mac de entrega. |
| R3 (*) Comparación de modelos | `docs/evaluation/model-selection-2026-11-02.md`; corridas E2 Nomic, Qwen y BGE-M3 | 7, 10 | Parcial | Se compararon 2 LLM y 2 embeddings con el mismo corpus/dataset; ningún LLM superó G1 y falta revisión humana 0–5. |
| R4 (*) Embeddings y base vectorial | `IngestionWorker`, `SnapshotIndexBuilder`, `ChromaGenerationIndex`; pruebas de índice | 5, 8.5 | Cumple | BGE-M3 requiere calibración propia antes de poder sustituir a Nomic. |
| R5 (*) RAG con fuentes | `SnapshotRetriever`, `PromptBuilder`, `verify_answer`; Recall@5 0.925 y Hit@5 0.950 | 6, 8.5, 10 | Parcial | Precisión de citas del chat 0.634/0.708, inferior a G1=0.80. |
| R6 (*) Arquitectura en capas | `docs/architecture/diagrams.md`; `backend/tests/test_architecture.py`; C1–C7/T1–T2 | 5, 8 | Cumple | La composición concreta centraliza dependencias; debe vigilarse el tamaño de `composition.py` y `sqlite.py`. |
| R7 (*) API REST | `presentation/api.py`; `/docs`; `/openapi.json`; pruebas de API | 8.1, anexo B | Cumple | La documentación viva requiere el servicio levantado. |
| R8 (*) Web por HTTP | `frontend/src/api/client.ts`; `frontend/e2e/api-boundary.spec.ts`; proxy `/api/v1` | 5 | Cumple | Sin acceso directo a Ollama, Chroma o SQLite detectado. |
| R9 Evaluación | `evaluation/datasets/`; `evaluation/runs/`; runner E1/E2/layers/calibration | 10 | Parcial | Falta revisión humana firmada, feedback real suficiente, concurrencia y repetición de latencias. |
| R10 Reproducibilidad | `README.md`, `pyproject.toml`, `frontend/package-lock.json`, `docs/operations/local-operations.md` | 12 | Parcial | No consta reproducción desde clon limpio en un segundo equipo. |
| R11 (*) Informe técnico | Este informe Word/PDF/Markdown, diez diagramas y nueve ADR | 1–12 | Cumple documentalmente | La aceptación final corresponde al docente. |
| R12 (*) Más allá de chatbot | `POST /api/v1/breed-analyses`; vista BreedMatch; ranking determinista y artefacto estructurado | 2, 8.10 | Cumple con reserva | Falta evidencia de aprobación docente de la ficha de idea. |
| C1 API | Pydantic/FastAPI, sobre de error estable y endpoints mínimos | 8.1 | Cumple | — |
| C2 Orquestación/agente | `BreedAnalysisService`, `QueryOrchestrator`, máximo 2 iteraciones | 6, 8.2 | Cumple | G13 sólo 0.67 en los seis casos originalmente etiquetados. |
| C3 Guardrails | Cuatro controles de entrada; esquema/citas/contexto en salida; 21 casos | 6, 8.3, 10 | Cumple en dataset | La muestra no demuestra resistencia universal a evasiones. |
| C4 Caché | Exacta y semántica, TTL 3600/1800 s, umbral 0.85, partición y snapshot | 6, 8.4 | Cumple con riesgo | Margen de 0.022 frente al par contradictorio más cercano; muestra pequeña. |
| C5 Contexto | 180 tokens, solape 24, top-k 6, máximo 2 por sección, contexto 2500 tokens | 8.5 | Cumple | Umbral de suficiencia 0.68 provisional y no transferible a BGE-M3. |
| C6 Router/gateway | Política determinista simple/complex; timeout 120 s; 1 reintento; fallback local | 7, 8.6 | Cumple mecanismo | La selección de LLM sigue provisional por G1. |
| C7 Adaptadores | `ports/interfaces.py`; SQLite, Chroma, filesystem, Ollama | 5, 8.7 | Cumple | Sustituir SQLite exigiría dividir el adaptador monolítico. |
| T1 Observabilidad | `TraceRecorder`, SQLite, `/admin/metrics`, etapas y códigos sin texto protegido | 8.8 | Cumple | No hay exportador Prometheus ni prueba de carga. |
| T2 Feedback | Feedback útil/no útil y comentario ligado a análisis/traza | 8.9 | Parcial | No hay reentrenamiento automático ni muestra de feedback real analizada. |
| A1 Creatividad/valor | Recomendación estructurada, ranking, cobertura y citas | 2 | Evidencia aportada | Validación con usuarios pendiente. |
| A2 Contexto/RAG | Ingesta, embeddings, Chroma, recuperación y fuentes | 5, 8.5, 10 | Evidencia aportada | G1 del chat pendiente. |
| A3 Capas | Cinco vistas y tabla de responsabilidades | 5 | Evidencia aportada | — |
| A4 Guardrails | Tabla de políticas y evaluación | 8.3, 10 | Evidencia aportada | Generalización no demostrada. |
| A5 Router/gateway/caché | ADR-02/03/07; evaluación layers | 7, 8.4, 8.6 | Evidencia aportada | Modelo complejo provisional. |
| A6 Agente | Secuencia y pruebas de terminación | 6, 8.2, 10 | Evidencia aportada | Mejora tras reformulación incompleta. |
| A7 Observabilidad/feedback | Trazas, métricas y rutas de feedback | 8.8, 8.9 | Evidencia parcial | Feedback de usuarios insuficiente. |
| A8 API/web | OpenAPI, React y prueba de frontera | 5, 8.1 | Evidencia aportada | — |
| A9 Demostración local | Ensayo 2026-11-02 documentado | 10, 12 | Parcial | No fue ensayo sin conexión ni demostración observada por evaluador. |
| A10 Presentación | Presentación y guion en `docs/deliverables/final/` | Anexo D | Evidencia aportada | Calidad oral sólo se evalúa en vivo. |
| B1 Idea, dominio y requisitos | Ficha, corpus, tabla de requisitos y escenarios | 2–4 | Cubierto | Reservas R1/R12 explícitas. |
| B2 Vistas estructurales | Figuras 1–5 y análisis por vista | 5 | Cubierto | — |
| B3 Secuencias | Figuras 6–10 y flujos/alternativas | 6 | Cubierto | — |
| B4 ADR | Nueve ADR; estados y consecuencias | 9 | Cubierto | ADR-07 provisional; README de ADR-08 quedó desactualizado respecto del archivo y la corrida BGE-M3. |
| B5 Modelos/router | Dos LLM y dos embeddings, mismas preguntas/corpus | 7 | Cubierto con brecha | G1 y revisión humana pendientes. |
| B6 Evaluación | Metodología, resultados, errores y validez | 10 | Cubierto con brecha | Métricas faltantes declaradas “no evaluadas”. |
| B7 Redacción/formato/reproducibilidad | Word, PDF, Markdown, referencias, anexos y matriz | 1–12 | Cubierto | Índice automático debe actualizarse al abrir Word si la aplicación no lo recalcula. |

## Brechas prioritarias

1. Firmar la revisión humana de relevancia, fidelidad y español; no presentar los CSV sin puntuar como evaluación humana.
2. Confirmar el derecho de uso académico del corpus y evitar redistribuir el PDF si no existe autorización.
3. Repetir el benchmark de LLM hasta obtener estimaciones estables; una ejecución y un timeout por modelo no permiten inferir capacidad sostenida.
4. Ejecutar y registrar un ensayo completo sin conexión, una reproducción desde clon limpio y una prueba de concurrencia.
5. Incorporar evaluación independiente de especialistas y usuarios antes de describir BreedMatch como recomendador validado.
