# Cobertura de la rúbrica — K9 BreedMatch

Auditoría al 7 de noviembre de 2026. Fuente normativa: `docs/references/Proyecto_integrador_RAG.pdf`. Regla de lectura: **Cumple** sólo cuando existe implementación y evidencia; **Parcial** cuando existe implementación con una brecha medida; **Pendiente** cuando falta el entregable o la validación. La presentación sintetiza el informe, pero no lo sustituye.

| Criterio de la rúbrica | Evidencia real | Diapositiva o demostración | Brecha detectada |
|---|---|---|---|
| R1* Dominio y corpus propio ≥50 páginas | Corpus de 243 páginas, SHA-256 y dataset `k9-reference-v2`; `README.md` | 3, 7 | Cumple; derechos de autor, no redistribuible; confirmar permiso académico |
| R2* Ejecución local | Ollama en loopback, gateway sin rutas cloud, preflight | 6, demo | Parcial: falta ensayo final con red desconectada |
| R3* 2 LLM + 2 embeddings | Corridas E2 de Llama/Qwen y Nomic/BGE-M3; ADR-07/08 | 16–18 | Parcial: ningún LLM supera G1; revisión humana pendiente |
| R4* Embeddings en base vectorial | `IngestionWorker`, `SnapshotIndexBuilder`, Chroma; 786 vectores | 7, 12 | Cumple |
| R5* RAG con fuentes | Recall@5 0.925, Hit@5 0.950; citas por página | 8, 13, 25 | Parcial: citas del chat 0.634–0.708 < 0.80 |
| R6* Arquitectura C1–C7, T1–T2 | diagramas 3/4; prueba de arquitectura | 5, 9, 10 | Cumple |
| R7* API REST documentada | FastAPI `/api/v1`, OpenAPI y pruebas de compatibilidad | 22, demo | Cumple |
| R8* Web sólo consume API | `API_BASE=/api/v1`; E2E de frontera | 6, 22 | Cumple |
| R9 Evaluación por capa | E1, E2, layers, calibration; puertas versionadas | 24–26 | Parcial: revisión humana y latencia agregada pendiente |
| R10 Reproducibilidad | README, lockfiles, preflight, operaciones | 27, demo | Parcial: falta clon limpio en otra máquina |
| R11* Informe técnico | DOCX/PDF final y paquete de evidencia | 28 | Cumple como entregable; quedan campos académicos editables |
| R12* Más allá de chatbot | BreedMatch por defecto; `POST /breed-analyses`; prueba E2E | 2–4, demo | Cumple; ficha aprobada por docente pendiente |
| C1 Interfaz | `presentation/api.py`, Pydantic, errores estables | 9, 22 | Cumple |
| C2 Orquestación/agente | `BreedAnalysisService`, `QueryOrchestrator`, máx. 2 | 9, 15, 21 | Cumple; G13 no obligatoria = 0.67 en casos originales |
| C3 Guardrails | 4 verificaciones entrada + salida; detección 1.0, FP 0.0 | 14, 19 | Cumple en dataset; riesgo fuera de distribución |
| C4 Caché | exacta/semántica, 0.85, TTL, snapshot | 14, 20 | Cumple; margen semántico estrecho declarado |
| C5 Contexto | Retriever k=6, ≤2/sección, suficiencia, matcher | 7, 8, 13 | Cumple; umbral de suficiencia provisional |
| C6 Router/gateway | router determinista, timeout 120 s, reintento y fallback local | 9, 18, 21 | Mecanismo cumple; asignación de modelos provisional |
| C7 Datos/modelos | adaptadores SQLite, Chroma, Ollama y archivos tras puertos | 6, 9, 10 | Cumple |
| T1 Observabilidad | trazas por etapa y `/admin/metrics` | 21, demo | Cumple; falta muestra longitudinal |
| T2 Retroalimentación | feedback ligado a análisis/traza/modelo | 21, 22, demo | Parcial: falta incorporarlo a evaluación real |
| A1 Propuesta de valor | flujo BreedMatch, decisión determinista, citas | 2–4 | Cumple |
| A2 Embeddings y RAG | preparación/consulta, parámetros y ejemplo | 7, 8 | Cumple; justificación de algunos umbrales provisional |
| A3 Arquitectura en capas | cinco vistas y mapeo código | 5, 6, 9–11 | Cumple |
| A4 Guardrails | controles, política y evidencia | 19 | Cumple en dataset |
| A5 Router, gateway y caché | políticas y trade-offs | 18, 20 | Cumple |
| A6 Agente | ciclo, herramientas, límite y terminación | 15, 21 | Cumple |
| A7 Observabilidad/feedback | campos de traza y vínculo | 21 | Parcial: feedback real no evaluado |
| A8 API/web | tabla endpoints y frontera HTTP | 22 | Cumple |
| A9 Demo local | guion reproducible de 5 minutos | 23 y archivo de guion | Pendiente de ensayo final |
| A10 Calidad de presentación | ruta principal 15 min, apéndice, notas y diagramas legibles | todo el archivo | Requiere completar nombre/institución/docente |
| B1 Idea/dominio/requisitos | informe §§1–3 | 2–4, 28 | Cumple en informe |
| B2 Vistas estructurales | informe §4, diagramas 1–5 | 5, 6, 9–11, apéndice | Cumple |
| B3 Secuencias | informe §5, diagramas 6–10 | 12–15 y apéndice | Cumple |
| B4 ADR | ADR-01…09 | 18–20, apéndice | Cumple; separar evidencia medida de comparación conceptual |
| B5 Modelos/enrutamiento | informe §6, corridas y ADR | 16–18 | Parcial por G1/revisión humana |
| B6 Evaluación | informe §9 y corridas versionadas | 24–26 | Parcial por revisión humana y especialista |
| B7 Redacción/reproducibilidad | informe, README, operaciones | 27–28 | Parcial por clon limpio pendiente |

## Brechas que deben declararse en la defensa

1. Ningún LLM supera la puerta G1 de precisión de citas del chat (0.80).
2. Falta firma de revisión humana de relevancia/fidelidad y validación por especialista canino.
3. Falta el ensayo final sin conexión y la reproducción desde un clon limpio en otra máquina.
4. El permiso académico del corpus debe confirmarse; el PDF no se redistribuye.
5. Los resultados perfectos corresponden a datasets acotados y no demuestran generalización.

