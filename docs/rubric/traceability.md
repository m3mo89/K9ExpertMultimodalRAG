# Matriz de trazabilidad — rúbrica del proyecto integrador

Estado al 2026-11-06. Regla: un requisito sólo figura como **Cumple** si enlaza evidencia que supera sus puertas (`docs/evaluation/acceptance-gates-v1.md`). Estados posibles: **Cumple**, **Parcial** (implementado, con brecha medida o revisión pendiente) y **Pendiente**.

## Requisitos R1–R12

| Id | Requisito | Implementación | Pruebas y evidencia | Estado |
|---|---|---|---|---|
| R1 (*) | Dominio y corpus propio (≥ 50 páginas) | Perros de caza; enciclopedia de 243 páginas (`README.md`, sección Corpus) | `evaluation/datasets/k9-reference-v2.json` (SHA-256 del PDF); registro de ingesta en `docs/evaluation/model-selection-2026-11-02.md` | Cumple. La licencia del PDF impide redistribuirlo; se documenta cómo adquirirlo |
| R2 (*) | Ejecución local sin APIs en la nube | Ollama en loopback; `RoutedOllamaGateway` sin rutas externas | `backend/tests/test_routing.py::test_gateway_never_falls_back_to_an_unconfigured_external_alias`; `frontend/e2e/api-boundary.spec.ts`; `scripts/preflight.py` | Parcial: falta el ensayo sin conexión en la Mac de entrega (9.6) |
| R3 (*) | ≥ 2 LLM y ≥ 2 modelos de embeddings comparados | `python -m k9_expert.evaluation run --text-model …` y `--embedding-model …` | LLM: `evaluation/runs/20261102T045033Z-E2-7e3065.json`, `…045419Z-E2-60bc77.json`; embeddings: Nomic `…045033Z-E2-7e3065.json`, BGE-M3 `evaluation/runs/20261107T033817Z-E2-aad176.json`; ADR-07, ADR-08 | **Parcial**: 2 LLM y 2 embeddings medidos; ambos embeddings superan G2–G4, pero ningún LLM supera G1 y falta la revisión humana |
| R4 (*) | Embeddings en base vectorial | `IngestionWorker`, `SnapshotIndexBuilder`, `ChromaGenerationIndex` | `backend/tests/test_vector_index.py`, `test_pipeline.py`; 786 vectores en staging | Cumple |
| R5 (*) | RAG con fuentes | `SnapshotRetriever`, `PromptBuilder`, `verify_answer`; citas por página en BreedMatch | E2: Recall@5 0.925, Hit@5 0.95; BreedMatch: páginas citadas en las esperadas 0.93 | **Parcial**: precisión de cita del chat 0.63–0.71 < 0.80 (G1) |
| R6 (*) | Arquitectura en capas con C1–C7, T1, T2 | Ver tabla de capas | `docs/architecture/diagrams.md` (diagramas 3 y 4); `backend/tests/test_architecture.py` | Cumple |
| R7 (*) | API REST documentada | FastAPI `/api/v1`, OpenAPI en `/docs` y `/openapi.json` | `backend/tests/test_breed_analysis_api.py`, `test_api_compatibility.py`; `GET /openapi.json` → 200 en el ensayo del 2026-11-02 | Cumple |
| R8 (*) | Web que consume la API sin llamar a modelos ni a la base vectorial | React; `API_BASE = '/api/v1'` | `frontend/e2e/api-boundary.spec.ts` (ninguna petición ni script conoce Ollama ni Chroma) | Cumple |
| R9 | Evaluación por capa con conjuntos de prueba | `k9_expert.evaluation` (E1, E2, `layers`, `calibrate`) | `evaluation/runs/20261102T050027Z-LAYERS-6fd1ec.json`; `docs/evaluation/model-selection-2026-11-02.md` | Parcial: revisión humana de relevancia y fidelidad pendiente; la reducción de latencia por caché sólo se observa en el ensayo (20 ms frente a 13.3 s) |
| R10 | Reproducibilidad | `README.md`, `docs/operations/local-operations.md`, `scripts/preflight.py`, `pyproject.toml`, `package-lock.json` | Comandos del README ejecutados contra el servicio el 2026-11-02 | Parcial: falta reproducir desde un clon limpio en otra máquina |
| R11 (*) | Informe técnico con arquitectura, secuencias, ADR, modelos y evaluación | Insumos: `docs/architecture/diagrams.md`, `docs/adr/`, `docs/evaluation/` | Paquete de evidencia en `docs/rubric/report-evidence.md` | Pendiente: el PDF del informe lo redacta el autor |
| R12 (*) | Producto más allá de un chatbot | K9 BreedMatch, vista por defecto y `POST /api/v1/breed-analyses` | `frontend/e2e/responsive.spec.ts::the default view completes a BreedMatch analysis without chat`; `BreedMatchView.test.tsx` | Cumple (falta la ficha aprobada por el docente) |

## Capas C1–C7 y transversales T1–T2

| Capa | Implementación | Requisito mínimo y evidencia | Estado |
|---|---|---|---|
| C1 Interfaz | `presentation/api.py` (Pydantic, sobre de error estable) | Endpoints de la sección 6: health, documentos, `breed-analyses`, feedback, `admin/metrics`, `configuration`; `test_breed_analysis_api.py` | Cumple |
| C2 Orquestación y agente | `BreedAnalysisService`, `QueryOrchestrator`, `DomainPreservingReformulator` | Ciclo acotado (máx. 2): terminación 1.0, 6/6 reformulados generan (ADR-05) | Cumple; G13 (no obligatoria) 0.67 en los casos originales |
| C3 Guardarraíles | `InputGuardrailChain` (4 verificaciones), `OutputGuardrailChain` + `verify_answer` + `safety_frame` | Detección 1.0, falsos bloqueos 0.0 (G8, G9); `test_guardrails.py` (ADR-04) | Cumple |
| C4 Caché | `QueryResponseCache`, `AnalysisResponseCache`, `SqliteResponseCache`, `CacheInvalidator` | Exacta y semántica, umbral 0.85 calibrado, TTL, invalidación por snapshot; 0 reutilizaciones indebidas (G10, ADR-03) | Cumple, con riesgo de margen declarado |
| C5 Contexto | `SnapshotRetriever`, `SemanticRetriever` (k = 6, ≤ 2 por sección), `EvidenceSufficiencyPolicy`, `PromptBuilder`, `DeterministicBreedMatcher` | Fragmentación justificada (ADR-01); Recall@5 0.925 | Cumple; umbral de suficiencia provisional |
| C6 Enrutador y gateway | `ComplexityRouter`, `RoutedOllamaGateway` | 2 modelos enrutados (llama3.2:3b `simple`, qwen3.5:2b `complex`); tiempo límite, reintento y respaldo; router 1.0 (G11, ADR-02) | Cumple el mecanismo; elección de modelos provisional (ADR-07) |
| C7 Acceso a datos y modelos | `infrastructure/` (SQLite, Chroma, Ollama, archivos) detrás de `ports/interfaces.py` | Un adaptador por recurso; ADR-06 | Cumple |
| T1 Observabilidad | `TraceRecorder`, `TraceRepository`, `TelemetryService._layers` | Traza por consulta con etapas, guardarraíles, caché, ruta, modelo, respaldo e iteraciones; `/admin/metrics` → `recent.layers`; `test_breed_analysis_service.py::test_layer_metrics_cover_breed_match_without_exposing_text` | Cumple |
| T2 Retroalimentación | `POST /answers/{id}/feedback`, `POST /breed-analyses/{id}/feedback` | Ligada a traza, ruta y modelo (`breed_match_feedback`); retención de comentarios | Parcial: falta incluir retroalimentación real en el análisis de evaluación |

## Brechas que impiden declarar cumplimiento total

1. G1, precisión de cita del chat (R3, R5): no superada por ningún modelo.
2. Revisión humana pendiente: hojas `*.review.csv` y firma de los datasets (8.5).
3. Ensayo completo sin conexión en la Mac de entrega (9.6).
4. Informe técnico en PDF (R11).
