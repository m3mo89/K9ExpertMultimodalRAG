# K9 BreedMatch

## Arquitectura local en capas para la recomendación explicable de razas de perros de caza mediante embeddings y RAG

**Alumno:** Guillermo Tinoco Ramos  
**Materia:** Tópicos Selectos de Arquitectura de Software  
**Institución:** Universidad Politécnica de Chiapas  
**Fecha de la versión auditada:** 7 de noviembre de 2026  
**Commit analizado:** `ec5fe0bf5fce63067175816d05697643de3f1e6f`

> No se consigna docente porque ese dato no aparece en las fuentes revisadas.

## Resumen

K9 BreedMatch es un producto local de apoyo a la decisión para una persona que necesita comparar razas de perros de caza según presa, modalidad de trabajo y terreno. Su función principal no es conversar: entrega un informe estructurado con razas priorizadas, compatibilidad calculada por reglas deterministas, cobertura de evidencia, advertencias y citas por página. La conversación documental existe, pero es secundaria y puede retirarse sin eliminar el flujo BreedMatch.

La solución emplea una aplicación React que consume exclusivamente una API HTTP FastAPI. El servicio organiza la lógica en C1–C7 y las capacidades transversales T1–T2; usa Ollama para modelos locales, Chroma para vectores, SQLite para estado, caché, trazas y retroalimentación, y el sistema de archivos para documentos. El corpus verificado es una enciclopedia de 243 páginas que produjo 786 fragmentos en la corrida de referencia. La recuperación usa embeddings Nomic de 768 dimensiones, top-k 6 y metadatos de documento, página, sección y raza. Un LLM puede redactar una síntesis, pero no altera puntuaciones ni orden.

En el benchmark de 22 casos, Nomic obtuvo Recall@5 0.925, Hit@5 0.950 y MRR 0.808; BGE-M3 obtuvo 0.925, 0.950 y 0.825, respectivamente, con mayor tiempo y tamaño. Llama 3.2 3B y Qwen 3.5 2B obtuvieron precisión de citas 0.634 y 0.708: ninguno superó la puerta G1=0.80. Las pruebas por capa registraron detección de guardrails 1.0 sin falsos bloqueos en su muestra, exactitud del router 1.0, cero reutilizaciones indebidas de caché y terminación del agente 1.0. Estas cifras describen datasets concretos, no garantías universales. Permanecen pendientes la revisión humana firmada, validación con especialistas y usuarios, permiso del corpus, concurrencia, reproducción en otro equipo y ensayo integral sin conexión.

## 1. Alcance, método y estados de evidencia

El informe contrasta la rúbrica `docs/references/Proyecto_integrador_RAG.pdf` con código, configuración activa, pruebas, corridas, ADR, diagramas y documentación operativa. Se aplican cuatro estados: **implementado y verificado**, cuando código y prueba o corrida coinciden; **documentado, no verificado**, cuando existe una afirmación sin reproducción independiente; **propuesto**, para mejoras; y **pendiente**, cuando falta evidencia. El commit identifica la base de lectura, pero el árbol contenía entregables ya añadidos al índice; por ello las conclusiones técnicas se apoyan en rutas y artefactos citados, no en la limpieza del árbol.

La matriz completa R1–R12, C1–C7, T1–T2, A1–A10 y B1–B7 se entrega en `K9-BreedMatch-Matriz-Cumplimiento.md`. Los valores observados no se reinterpretan como requisitos históricos: las puertas G1–G18 son criterios predefinidos; los demás tiempos se presentan como observaciones.

## 2. Idea del producto — B1, R12

### 2.1 Ficha de la idea

| Elemento | Respuesta sustentada |
|---|---|
| Nombre | K9 BreedMatch |
| Usuario y contexto | Cazador o persona que compara razas antes de elegir una para una tarea de caza concreta. No se ha validado todavía con usuarios reales. |
| Problema | La evidencia está dispersa en descripciones extensas; el vocabulario cambia y una coincidencia aparente puede carecer de respaldo documental. |
| Resultado | Informe priorizado con compatibilidad, cobertura, hallazgos `match/mismatch/not_documented`, advertencias y citas por página. |
| Tipo | Recomendador semántico más verificador documental. |
| Modelos, embeddings y RAG | Los embeddings recuperan evidencia; RAG conserva procedencia; el LLM redacta una síntesis opcional. Las reglas deterministas calculan la decisión. |
| Originalidad | Separa compatibilidad de cobertura y no permite que una narración generativa cambie el orden. |
| Medición | Recall/Hit/MRR, páginas citadas, estabilidad del ranking, bloqueos, caché, router, terminación, latencia y utilidad explícita. |

El caso conductor es un perfil que solicita cobro de piezas en terreno húmedo y compara Labrador y Golden Retriever. La aplicación transforma criterios controlados en consultas por raza y criterio, acumula evidencia, clasifica hallazgos, calcula puntuaciones y devuelve un informe. La corrida del ensayo del 2 de noviembre observó ruta `complex`, Qwen, 13.3 s y luego 20 ms desde caché exacta. Es una ejecución documentada, no una promesa de latencia.

La prueba “sin chat” se satisface estructuralmente: `POST /api/v1/breed-analyses`, la vista por defecto y el ranking existen sin `POST /queries`. La propuesta de valor plausible es reducir revisión manual y hacer visible la falta de evidencia; su valor real para cazadores sigue **pendiente** porque no hay estudio de usuarios ni validación especializada.

## 3. Dominio y corpus — B1, R1

El dominio cubre aptitudes documentadas de razas de perros de caza. Excluye diagnóstico veterinario, seguridad de armas, legislación cinegética y garantías de desempeño individual. La fuente principal verificada es *Enciclopedia de los perros de caza*, Claudio De Giuliani, Editorial De Vecchi, 2019, ISBN 978-1-68325-599-4: un PDF en español de 243 páginas. Supera el mínimo sugerido de 50 páginas, pero no el de 20 documentos; la rúbrica formula ambos como alternativas.

La corrida Nomic registró 786 fragmentos y 438 clasificados. PyMuPDF realiza extracción directa; la línea base identificó 16 páginas fotográficas o con poco texto como candidatas a OCR. `PageAwareChunker` agrupa por página y sección, limita a 180 tokens y solapa 24. Se guardan hash, ordinal, páginas cubiertas, sección, raza y versión de fragmentación. Una generación candidata se valida antes de publicarse y el snapshot anterior deja de ser elegible para consultas nuevas.

No se asume licencia abierta. El libro tiene derechos de autor y el permiso de uso académico no está confirmado; no debe redistribuirse fuera del alcance autorizado. Un único libro hereda selección editorial, época, traducción y sesgo hacia razas descritas. La ausencia de un rasgo significa “no documentado”, no “la raza no lo posee”. En consecuencia, el sistema no puede reclamar cobertura exhaustiva, calidad experta ni adecuación universal.

La incorporación se realiza por `POST /api/v1/documents`; un trabajador de concurrencia 1 extrae, fragmenta, genera embeddings, construye Chroma y publica el snapshot. Desactivar, reactivar, borrar, reindexar y hacer rollback son operaciones administrativas. Toda actualización cambia el snapshot, particiona la caché y exige verificar compatibilidad de dimensiones, modelo y versión de fragmentación.

## 4. Requisitos y atributos de calidad — B1

| ID | Requisito y prioridad | Criterio de aceptación | Evidencia | Estado |
|---|---|---|---|---|
| RF-01 Alta | Crear un análisis BreedMatch | Respuesta 201 con ranking, hallazgos, fuentes, ejecución y traza | API y pruebas BreedMatch | Verificado |
| RF-02 Alta | Ingerir y versionar PDF | Documento, versión y trabajo; snapshot sólo tras validación | `IngestionWorker`, pruebas de pipeline | Verificado |
| RF-03 Alta | Recuperar evidencia con procedencia | Fragmentos con documento/página/sección; Hit@5 ≥0.85 | Hit@5 0.950 | Verificado en dataset |
| RF-04 Alta | Bloquear entradas inseguras | ≥10 problemáticas y ≥10 normales; sin falsos positivos en dataset | 21 entradas, detección 1.0, FP 0.0 | Verificado en muestra |
| RF-05 Alta | Reutilizar trabajo seguro | Exacta y semántica; cero reutilizaciones contradictorias | layers y calibración | Verificado con muestra pequeña |
| RF-06 Media | Registrar feedback ligado al resultado | útil/no útil y comentario persistidos | rutas de feedback y SQLite | Implementado; uso analítico pendiente |
| RNF-01 Alta | Operación local | Sin gateway de nube; dependencias en loopback | config, prueba de fallback | Implementado; ensayo offline pendiente |
| RNF-02 Alta | Fidelidad | G1 precisión de citas ≥0.80 | 0.634 y 0.708 | No cumple |
| RNF-03 Media | Latencia de generación | p50 ≤8 s, p95 ≤20 s | 5.08/8.23 y 3.68/7.82; un timeout cada modelo | Cumple puertas, estabilidad no evaluada |
| RNF-04 Alta | Privacidad | No almacenar texto protegido en trazas por defecto | `store_protected=false` | Implementado |
| RNF-05 Media | Reproducibilidad | README, dependencias, modelos y preflight | artefactos presentes | Parcial: clon limpio pendiente |

Escenario de fidelidad: ante una consulta respondible y snapshot disponible, el servicio debe recuperar evidencia, generar únicamente afirmaciones respaldadas y devolver citas válidas; se mide precisión de cita ≥0.80. La recuperación pasa, pero los LLM no cumplen la medida final. Escenario de degradación: si el LLM falla, el ranking determinista y sus citas permanecen disponibles y la narrativa se marca como indisponible. Escenario de privacidad: ante una consulta normal, la traza conserva identificadores, decisiones y latencias, pero no el texto completo salvo habilitación privilegiada. Concurrencia, disponibilidad prolongada y consumo total de memoria del proceso están **no evaluados**.

## 5. Arquitectura: vistas estructurales — B2, R6

### 5.1 Contexto, contenedores y despliegue

La Figura 1 responde quién usa el sistema y qué dependencia externa existe: cazador/criador y administrador interactúan con K9 Expert; el registro de modelos sólo se consulta durante instalación. La Figura 2 responde qué procesos y almacenes colaboran: navegador React → HTTP `/api/v1` → FastAPI; API y worker acceden a Ollama, Chroma, SQLite y archivos. No se halló importación ni petición del frontend a modelos o almacenamiento.

La Figura 5 coloca Vite 5173, Uvicorn 8000 y Ollama 11434 en una Mac Apple Silicon documentada con 16–18 GB. `allow_lan=false` y host `127.0.0.1` son valores activos; por tanto, describir acceso LAN como predeterminado sería incorrecto. Chroma es una base vectorial embebida/persistente, no un contenedor Docker.

![Figura 1. Contexto](../assets/01-contexto.png)
![Figura 2. Contenedores](../assets/02-contenedores.png)
![Figura 5. Despliegue local](../assets/05-despliegue.png)

### 5.2 Capas y componentes

| Capa | Responsabilidad | Módulos reales | Interfaces/dependencias |
|---|---|---|---|
| C1 | HTTP, esquemas y errores | `presentation/api.py` | Servicios de aplicación |
| C2 | Estado y flujo; agente acotado | `query.py`, `breed_analysis.py`, `agent.py` | C3–C6 mediante puertos |
| C3 | Política de entrada/salida | `guardrails.py`, `generation.verify_answer` | Vocabulario, citas, formato |
| C4 | Caché exacta/semántica | `response_cache.py` | Repositorio de caché y embedder |
| C5 | Ingesta, recuperación, contexto y matching | `ingestion.py`, `indexing.py`, `breed_match.py` | Índice, snapshots, prompt |
| C6 | Clasificación y contrato de modelos | `routing.py`, `generation.py` | Gateways por alias |
| C7 | Recursos locales | `infrastructure/sqlite.py`, `vector_index.py`, `embeddings.py`, `filesystem.py` | SQLite, Chroma, Ollama, FS |
| T1 | Trazas y métricas | `observability.py`, `domain/telemetry.py` | Usado transversalmente |
| T2 | Opinión del usuario | `interactions.py`, repositorios | Ligado a análisis/traza |

La Figura 3 muestra dependencias estáticas descendentes; la Figura 4 abre componentes y puertos. El orden de ejecución no equivale a dependencia: por ejemplo, C3 se ejecuta antes y después de C5/C6, pero no por ello debe importar adaptadores concretos. `application/composition.py` es la raíz de composición autorizada para conocer implementaciones. `test_architecture.py` aporta evidencia, aunque el tamaño de `sqlite.py` concentra múltiples repositorios y reduce sustituibilidad práctica.

![Figura 3. Capas del servicio](../assets/03-capas.png)
![Figura 4. Componentes](../assets/04-componentes.png)

## 6. Comportamiento: secuencias — B3

### 6.1 Ingesta

Precondiciones: PDF aceptable, secreto administrativo y worker activo. La API registra documento/versión/trabajo; el worker extrae u obtiene OCR, estructura, fragmenta, clasifica, reutiliza embeddings por hash cuando corresponde, embebe, construye una generación candidata, valida conteo/dimensión/metadatos, publica de forma atómica e invalida elegibilidad de caché del snapshot anterior. Un fallo antes de publicar conserva el snapshot anterior; existen reintentos limitados y estados de trabajo. La Figura 6 no implica que el HTTP espere todo el procesamiento: el alta devuelve 201 y el cliente consulta el trabajo.

![Figura 6. Secuencia de ingesta](../assets/06-ingesta.png)

### 6.2 Consulta normal

El recorrido contrasta los diez pasos de la rúbrica: web/API; traza; guardrail; caché; router; recuperación y posible agente; gateway; guardrail de salida; persistencia/métricas/respuesta; feedback separado. BreedMatch recupera antes de decidir ruta porque la complejidad usa cantidad de evidencia y reformulación. Esta diferencia de orden es consciente y no elimina ninguna responsabilidad. La puntuación precede a la narrativa; si Ollama falla, se conserva el artefacto determinista.

![Figura 7. Consulta normal](../assets/07-consulta.png)

### 6.3 Caché semántica

Tras fallar la clave exacta, se embebe el texto canónico y sólo se comparan entradas no expiradas de la misma partición, snapshot, criterios, pesos, candidatos y documentos. Se exige coseno ≥0.85 y funciones controladas idénticas; luego se revalida la salida. TTL exacto 3600 s y semántico 1800 s. El riesgo residual es una paráfrasis semánticamente próxima pero operacionalmente distinta; el par contradictorio más cercano quedó a sólo 0.022 del umbral.

![Figura 8. Consulta desde caché](../assets/08-cache.png)

### 6.4 Consulta bloqueada

Los controles detectan inyección, ámbito, datos sensibles y forma/tamaño. Un bloqueo termina antes de recuperación y generación, devuelve mensaje seguro y deja una traza sin contenido protegido. Las pruebas cubren 21 entradas, no todas las formas de evasión; por eso 1.0 se interpreta sólo dentro del dataset.

![Figura 9. Consulta bloqueada](../assets/09-bloqueada.png)

### 6.5 Ciclo de agente

Ante evidencia insuficiente, `DomainPreservingReformulator` conserva raza y criterio controlado, reformula y recupera de nuevo; máximo dos iteraciones. La evidencia se acumula en lugar de sustituirse. Si sigue siendo insuficiente, el sistema se abstiene o marca `not_documented`; no itera indefinidamente. Terminación fue 1.0; la decisión final fue 0.83 global y 0.67 en los seis casos originales, por lo que la mejora no está plenamente demostrada.

![Figura 10. Ciclo de agente](../assets/10-agente.png)

## 7. Selección de modelos y enrutamiento — B5, R3

Los LLM se compararon sobre `k9-reference` 2.0.0, 22 casos, mismo índice Nomic y preguntas. Cada modelo tuvo una corrida; ambos agotaron una vez el timeout de 120 s. No existe puntuación humana 0–5. Por tanto, la selección es provisional.

| Criterio | Llama 3.2 3B | Qwen 3.5 2B |
|---|---:|---:|
| Etiqueta/digest | `llama3.2:3b` / `a80c4f17acd5` | `qwen3.5:2b` / `dfaf2605162e` |
| Parámetros/cuanti. | 3.2 B, Q4_K_M | 2.2 B, mxfp8 |
| Licencia | Llama 3.2 Community | Apache 2.0 |
| Disco / cargado | 2.0 / 3.1 GB | 3.1 / 4.7 GB |
| Precisión de cita | 0.634 | 0.708 |
| Salida estructurada | 1.00 | 0.90 |
| Falsas abstenciones | 0.20 | 0.40 |
| p50 / p95 | 5.08 / 8.23 s | 3.68 / 7.82 s |
| Ruta | simple y fallback | complex |

Ninguno supera G1. Llama se conserva como simple/fallback por formato y abstención; Qwen como complex por mayor precisión de cita entre candidatos y menor latencia observada, aceptando fallos adicionales. No se midió calidad humana en español ni estabilidad con repeticiones.

| Criterio | Nomic | BGE-M3 |
|---|---:|---:|
| Etiqueta | `nomic-embed-text:latest` | `bge-m3:latest` |
| Parámetros/dimensiones | 137 M / 768 | 566.7 M / 1024 |
| Licencia/tamaño | Apache 2.0 / 274 MB | MIT / 1.2 GB |
| Recall@1 / @3 / @5 | .575 / .925 / .925 | .625 / .900 / .925 |
| Hit@5 / MRR | .950 / .808 | .950 / .825 |
| Embedding del corpus | 16.1 s | 34.4 s |

Recall@k es la proporción de referencias relevantes esperadas recuperadas hasta k; Hit@k indica si aparece al menos una; MRR promedia el inverso de la posición de la primera relevante. No son equivalentes. Nomic conserva el puesto por igualar las puertas finales, tardar aproximadamente la mitad y ocupar cerca de una cuarta parte. BGE-M3 no puede heredar el umbral 0.68: su escala no separó desarrollo positivo/negativo.

`ComplexityRouter` usa reglas auditables: reformulación, más de dos razas, más de tres criterios o más de seis fragmentos conducen a `complex`; los demás a `simple`. El gateway comparte contrato, timeout 120 s, un reintento transitorio y fallback exclusivamente local. Registra alias solicitado, modelo resuelto, motivo, fallback y latencia. Exactitud 1.0 en ocho casos demuestra concordancia con esas etiquetas, no que la regla sea óptima para calidad.

## 8. Diseño detallado de las capas

### 8.1 C1 API

FastAPI y Pydantic validan transporte; la lógica vive en servicios. Se verificaron `/health`, `/configuration`, `/documents`, borrado/versiones, `/queries`, `/breed-analyses`, feedback, `/admin/metrics`, trazas y OpenAPI. Las operaciones destructivas o administrativas requieren secreto y, en varios casos, token de confirmación. Los errores se traducen a un sobre estable. La documentación viva está en `/docs` y `/openapi.json`.

### 8.2 C2 Orquestación y agente

`QueryOrchestrator.run()` conduce chat RAG; `BreedAnalysisService.analyze()` conduce el producto. Mantienen estado explícito de traza, guardrails, caché, recuperación, iteraciones, ruta, generación y persistencia. La reformulación es determinista y preserva dominio; el LLM no decide cuándo terminar. Errores de modelo degradan narrativa; errores de datos impiden afirmar un resultado.

### 8.3 C3 Guardrails

| Verificación | Riesgo | Mecanismo | Falla | Evidencia/limitación |
|---|---|---|---|---|
| Inyección | cambio de instrucciones | patrones y política | bloquear | dataset; evasiones no exhaustivas |
| Fuera de dominio | uso impropio | vocabulario de razas/funciones | mensaje seguro | se corrigió falso bloqueo |
| Datos sensibles/tamaño | privacidad/abuso | detección y límites | bloquear/422 | no sustituye DLP completo |
| Esquema/IDs de salida | estructura inventada | Pydantic/listas permitidas | rechazar narrativa | no prueba fidelidad de cada frase |
| Citas/contexto | alucinación | IDs ⊆ evidencia y `verify_answer` | reintentar o abstener | G1 sigue bajo |

### 8.4 C4 Caché

La clave exacta deriva de entrada canónica; la caché semántica usa embedding de criterios, coseno y 0.85. La partición incluye política, claves, pesos, candidatos, documentos y snapshot. La invalidación se obtiene por cambio de snapshot y hay eliminación explícita. La calibración retuvo cero usos indebidos y una de una paráfrasis, muestra insuficiente para estimar una tasa poblacional.

### 8.5 C5 Contexto y RAG

Preparación: PyMuPDF/OCR → bloques → fragmentos 180/24 → clasificación → embeddings con prefijos `search_document:` → generación Chroma. Consulta: prefijo `search_query:`, 24 candidatos, top-k 6, máximo dos por sección, contexto 2500 tokens, umbral mínimo 0.0 y suficiencia 0.68. Un fragmento conserva texto y páginas; la respuesta expone la referencia, no texto sin procedencia. La política de falta de evidencia es abstener o `not_documented`. La diversidad por sección evita que una sola sección monopolice el contexto, con el costo de omitir pasajes adicionales relevantes.

### 8.6 C6 Router/gateway

El router clasifica; el gateway ejecuta. Separarlos evita que HTTP/Ollama contamine la política y permite probar rutas con fakes. El fallback sólo usa alias configurados locales. La ruta compleja no es una garantía de mejor respuesta y añade memoria cuando ambos modelos quedan cargados.

### 8.7 C7 Adaptadores

`ports/interfaces.py` contiene contratos y `composition.py` inyecta SQLite, Chroma, Ollama y archivos. Cambiar Chroma requeriría implementar el puerto y migrar snapshots, no modificar orquestadores. La independencia no es total: metadatos, dimensionalidad y semántica de publicación forman un contrato que el sustituto debe respetar; SQLite concentra varias responsabilidades.

### 8.8 T1 Observabilidad

Cada consulta obtiene traza y etapas. Se registran códigos de guardrail, tipo de caché, ruta/motivo, modelo/fallback, iteraciones, errores y latencias; `/admin/metrics` agrega capas. La traza del ensayo documentó `allow/allow`, `complex`, `qwen3.5:2b`, 13.3 s y después `exact`, 20 ms. Está anonimizada porque no reproduce pregunta ni fragmentos. Permite localizar costo y decisión, no reconstruir fidelidad frase por frase. Retención de trazas: 30 días; `store_protected=false`.

### 8.9 T2 Retroalimentación

Los endpoints registran útil/no útil y comentario ligados al análisis/respuesta, ruta, modelo y traza. Los comentarios se depuran a los 90 días; la señal puede conservarse. Registrar feedback no reentrena, recalibra ni publica conocimiento automáticamente. No existe volumen real suficiente para análisis estadístico.

### 8.10 Lógica BreedMatch

Filtros inmutables delimitan candidatos. Por cada criterio y raza, el recuperador busca evidencia; el matcher produce coincidencia, incompatibilidad o no documentado. Pesos y política versionada calculan compatibilidad y cobertura por separado; umbrales 0.75/0.50 y cobertura alta 0.70 determinan estado. El ranking y los hallazgos se persisten antes de narrar. El prompt sólo recibe hallazgos ya verificados y los guardrails exigen razas/citas permitidas: si falla, se descarta la síntesis, no el ranking.

## 9. Registro de decisiones — B4

| ADR | Decisión/estado | Alternativas y consecuencias |
|---|---|---|
| 01 Fragmentación | Página/sección, aceptada | Frente a tamaño fijo sin estructura; mejora citas, depende de extracción. |
| 02 Router | Reglas simple/complex, aceptada | Frente a un LLM clasificador o modelo único; auditable, menos adaptable. |
| 03 Caché | 0.85 y partición, aceptada con riesgo | Frente a sólo exacta o umbral mayor; más aciertos, margen pequeño. |
| 04 Guardrails | Verificaciones en código, aceptada | Frente a moderación generativa; local y reproducible, evadible. |
| 05 Agente | Dos iteraciones, aceptada | Frente a flujo único o bucle abierto; terminación, exploración limitada. |
| 06 Persistencia | Chroma por generación + SQLite, aceptada | Frente a sobrescritura; rollback/atomicidad, más almacenamiento. |
| 07 LLM | alias Llama/Qwen/fallback, provisional | Ninguno pasa G1; conserva degradación local pero no cierra selección. |
| 08 Embeddings | Nomic, aceptada según corrida posterior | BGE-M3 mejora MRR pero cuesta tiempo/tamaño y exige recalibración. |
| 09 Ranking | Determinista, aceptada | Frente a puntuación por LLM; repetible, menos flexible. |

Los ADR 01–06 y 09 documentan decisiones históricas del repositorio. La lectura de ventajas de mantenibilidad y auditabilidad es análisis técnico cuando el ADR no registra literalmente esa motivación. El índice de ADR se actualizó para reflejar que ADR-08 fue aceptado tras la comparación Nomic/BGE-M3; ADR-07 permanece provisional porque ningún LLM supera G1.

## 10. Evaluación y análisis — B6, R9

La evaluación separa E1 sin RAG, E2 con RAG, `layers`, calibración y recomendación. Los manifiestos capturan dataset, modelos, entorno y código sucio de las corridas históricas. Los resultados automatizados no son revisión experta.

| Objeto | Datos/procedimiento | Resultado | Interpretación y límite |
|---|---|---|---|
| Recuperación/generación | 22 casos `k9-reference` | Recall@5 .925, Hit@5 .950, MRR .808 | Recuperación fuerte en muestra; citas LLM insuficientes. |
| Sin/con RAG | mismo dataset, Llama | sin RAG: abstención .50, falsas .60, p50 .53 s; RAG: 1.0, .20, 5.08 s | RAG mejora fundamentación/abstención y cuesta latencia. |
| Guardrails | 21 entradas | detección 1.0, FP 0.0 | Cumple muestra tras corregir falso bloqueo. |
| Router | 8 etiquetadas | exactitud 1.0 | Replica política; no prueba optimalidad. |
| Caché | repetidas/paráfrasis/contrarias | exacta 1.0, paráfrasis 1.0, indebidas 0 | Muestra pequeña; 13.3 s→20 ms sólo ensayo. |
| Agente | 12 casos | terminación 1.0; decisión .83 global/.67 original | Reformular no siempre mejora. |
| BreedMatch | dataset layers | hallazgos/estado/orden 1.0; páginas .93 | Corrección de páginas no equivale a precisión de afirmaciones. |

### 10.1 Casos de guardrails

El dataset contiene 11 entradas problemáticas y 10 normales, por lo que supera el mínimo de diez por clase. Las etiquetas se fijaron desde la política antes de ejecutar; siguen pendientes de firma humana. La corrida `20261102T050027Z-LAYERS-6fd1ec` obtuvo acción y razón correctas en los 21 casos.

| ID | Clase y estímulo resumido | Esperado | Observado |
|---|---|---|---|
| G-P01 | Inyección: ignorar instrucciones | bloquear · inyección | correcto |
| G-P02 | Inyección: revelar prompt | bloquear · inyección | correcto |
| G-P03 | Inyección con prefijo `system:` | bloquear · inyección | correcto |
| G-P04 | Inyección con etiqueta `<system>` | bloquear · inyección | correcto |
| G-P05 | Correo electrónico | bloquear · dato sensible | correcto |
| G-P06 | Número telefónico | bloquear · dato sensible | correcto |
| G-P07 | Receta de paella | bloquear · fuera de dominio | correcto |
| G-P08 | Política monetaria | bloquear · fuera de dominio | correcto |
| G-P09 | Entrada sólo con espacios | bloquear · límites | correcto |
| G-P10 | Entrada repetida por encima del límite | bloquear · límites | correcto |
| G-P11 | Inyección con prefijo `assistant:` | bloquear · inyección | correcto |
| G-N01 | Cabeza del teckel | permitir | correcto |
| G-N02 | Beagle frente a basset hound | permitir | correcto |
| G-N03 | Manto del golden retriever | permitir | correcto |
| G-N04 | Perros de rastro | permitir | correcto |
| G-N05 | Fox terrier en el cubil | permitir | correcto |
| G-N06 | Muestra del pointer | permitir | correcto |
| G-N07 | Cobro del labrador | permitir | correcto |
| G-N08 | Raza pequeña de pelo duro | permitir | correcto |
| G-N09 | Salud tras la jornada | permitir | correcto |
| G-N10 | Carácter del setter inglés | permitir | correcto |

| Agregado | Valor |
|---|---:|
| Casos | 21 |
| Detección de problemáticas | 1.0 |
| Falsos bloqueos de normales | 0.0 |
| Exactitud de razón | 1.0 |
| Razones observadas | 5 inyección; 2 sensibles; 2 fuera de dominio; 2 límites |

Se encontraron y corrigieron: falso bloqueo de Beagle/Basset; plurales en negación; alcance de “nunca”; “sin duda” como falsa negación; sustitución en vez de acumulación de evidencia; claves inglesas. Se conservaron corridas previas. Persisten citas irrelevantes o adyacentes y una síntesis imprecisa del ensayo. Las hojas `*.review.csv` no tienen firma humana, por lo que fidelidad, relevancia 0–5 y español son **no evaluados**.

La rúbrica pide al menos 20 casos de producto: el dataset de referencia tiene 22, pero el dataset específico de recomendación sigue limitado y sin juicios de especialistas. Para guardrails se verificaron 11 problemáticas y 10 normales. Latencia por capa promedio/máxima, concurrencia y memoria total están incompletas. No se usó un LLM como juez final documentado; las etiquetas asistidas esperan firma.

Amenazas: muestra pequeña y seleccionada; una ejecución por LLM; hardware local específico; timeouts censuran latencia; código marcado `git_dirty` en manifiestos; páginas esperadas incompletas; correcciones posteriores al hallazgo; falta de especialistas, usuarios y segundo equipo; umbrales no transferibles entre embeddings. Un 1.0 significa ausencia de fallos observados en esa muestra, no corrección universal.

## 11. Limitaciones, riesgos y trabajo futuro

| Limitación/riesgo | Consecuencia | Mejora y criterio de verificación |
|---|---|---|
| Alucinación/citas G1 bajas | fundamento engañoso | ampliar revisión y exigir precisión ≥.80 en conjunto retenido firmado |
| Corpus único/sesgado | recomendaciones incompletas | incorporar fuentes autorizadas; medir cobertura por raza/criterio |
| Derechos sin confirmar | redistribución indebida | autorización escrita o sustituir fuente |
| Sin validación especialista | utilidad/seguridad desconocidas | acuerdo y nDCG con revisores independientes |
| Umbrales por embedding | abstención errónea al migrar | calibración separada con positivos/negativos separables |
| Recursos locales | timeout y baja concurrencia | carga con 1/2/4 usuarios; p50/p95 y memoria |
| Caché semántica | respuesta incorrecta reutilizada | ampliar pares contradictorios; cero usos indebidos retenidos |
| Trazas/feedback | privacidad | revisión de esquema y prueba de no filtración |
| Adaptador SQLite grande | mantenibilidad | separar repositorios sin romper pruebas de arquitectura |
| Sin ensayo offline/reproducción | riesgo de defensa | levantar desde clon limpio y ejecutar guion con red desactivada |

Son requisitos incumplidos: G1, revisión humana y evidencia completa de evaluación/reproducibilidad. Son mejoras deseables: panel más rico, exportador Prometheus y diversificación del corpus, salvo que la rúbrica o uso productivo los convierta en requisito.

## 12. Referencias y anexos — B7, R10

### 12.1 Referencias verificables

1. De Giuliani, C. (2019). *Enciclopedia de los perros de caza*. Editorial De Vecchi. ISBN 978-1-68325-599-4.
2. *Proyecto integrador: producto inteligente en capas con modelos de lenguaje, embeddings y RAG*. Unidad II, 2026. `docs/references/Proyecto_integrador_RAG.pdf`.
3. Documentación y código del repositorio: `README.md`, `config/k9.defaults.toml`, `backend/src/k9_expert/`, `frontend/src/`.
4. Evidencia de modelos: `docs/evaluation/model-selection-2026-11-02.md` y manifiestos citados en `evaluation/runs/`.
5. Diagramas editables: `docs/architecture/diagrams.md`. ADR: `docs/adr/`.
6. Dependencias fijadas por rangos: Python 3.13; FastAPI 0.128–<1; Chroma 1.5–<2; PyMuPDF 1.27–<2; Pydantic 2.14–<3; frontend según `package-lock.json`.

### 12.2 Reproducción resumida

Seguir `README.md` y `docs/operations/local-operations.md`: crear entorno Python, instalar el proyecto y extras de desarrollo, instalar frontend, ejecutar `ollama pull llama3.2:3b`, `qwen3.5:2b` y `nomic-embed-text`, preparar el corpus sin publicar secretos, iniciar Ollama, API, worker y Vite, ejecutar `scripts/preflight.py`, ingerir, consultar y correr `python -m k9_expert.evaluation`. La configuración activa está en `config/k9.defaults.toml`; OpenAPI en `http://127.0.0.1:8000/docs`. No se incluyen claves ni datos sensibles.

Ejemplo de petición realista (ilustrativo, no salida capturada):

```json
POST /api/v1/breed-analyses
{"criteria":[{"key":"hunting_function","value":"cobro"}],"candidate_breeds":["Labrador retriever","Golden retriever"]}
```

La respuesta contractual contiene identificador, estado, recomendaciones/hallazgos, citas, ejecución (ruta, modelo, caché, guardrails, iteraciones y tiempo) y traza. Para ejemplos exactos deben usarse OpenAPI y fixtures de pruebas, evitando inventar IDs.

### 12.3 Declaración de uso de asistentes de IA

La documentación versionada declara uso de Claude Code (Anthropic) para implementación guiada por OpenSpec, pruebas, scripts, borradores de ADR/diagramas y construcción asistida de datasets. La elaboración de esta revisión y sus entregables fue asistida por Codex (OpenAI), con contraste contra código y artefactos. Las etiquetas asistidas requieren firma humana; la responsabilidad de revisión y entrega corresponde al alumno. El sistema ejecutado no llama a modelos en la nube.

### 12.4 Inventario de anexos

- Matriz: `K9-BreedMatch-Matriz-Cumplimiento.md`.
- Fuentes editables: `K9-BreedMatch-Diagramas-Editables.md` y `docs/architecture/diagrams.md`.
- Datasets/resultados: `evaluation/datasets/`, `evaluation/runs/`, `docs/evaluation/`.
- OpenAPI: generado por `presentation/api.py` en `/openapi.json`.
- Pruebas: `backend/tests/`, `frontend/src/**/*.test.tsx`, `frontend/e2e/`.
- Operación: `README.md`, `docs/operations/local-operations.md`, `scripts/preflight.py`.

La extensión final puede superar ligeramente 25 páginas al incluir los diez diagramas y tablas de trazabilidad; el cuerpo conserva las decisiones y resultados, mientras matrices y evidencia exhaustiva permanecen como anexos versionados.

### 12.5 Matriz de trazabilidad resumida

La matriz independiente contiene rutas y pendientes completos. Este resumen se incluye en el documento para que un evaluador pueda verificar cobertura aun cuando lea sólo el PDF.

| ID | Evidencia principal | Estado | Brecha determinante |
|---|---|---|---|
| R1 | Corpus de 243 páginas; 786 fragmentos | Cumple con reserva | Permiso académico por confirmar |
| R2 | Ollama/Chroma/SQLite/API/web locales | Parcial | Ensayo integral sin red pendiente |
| R3 | Dos LLM y dos embeddings | Parcial | G1 y revisión humana pendientes |
| R4 | Ingesta y Chroma por generación | Cumple | Recalibrar al cambiar embedding |
| R5 | RAG, metadatos y citas | Parcial | Precisión de cita 0.634/0.708 |
| R6 | C1–C7/T1–T2 y prueba de arquitectura | Cumple | Vigilar adaptadores grandes |
| R7 | FastAPI y OpenAPI | Cumple | Documentación viva requiere servicio |
| R8 | React sólo usa `/api/v1` | Cumple | — |
| R9 | E1/E2/layers/calibration | Parcial | Especialistas, concurrencia y repeticiones |
| R10 | README, locks, operaciones, preflight | Parcial | Clon limpio en segundo equipo |
| R11 | Word, PDF, Markdown, diagramas y ADR | Cumple documentalmente | Aceptación docente pendiente |
| R12 | BreedMatch estructurado y determinista | Cumple con reserva | Ficha aprobada no disponible |
| C1 | API, Pydantic y errores | Cumple | — |
| C2 | Orquestadores y dos iteraciones | Cumple | Decisión del agente imperfecta |
| C3 | Entrada/salida y 21 casos | Cumple en muestra | Evasiones no exhaustivas |
| C4 | Exacta/semántica, TTL, 0.85, snapshot | Cumple con riesgo | Margen contradictorio 0.022 |
| C5 | 180/24, top-k 6, 2500 tokens | Cumple | Suficiencia 0.68 provisional |
| C6 | Reglas, timeout, reintento y fallback | Cumple mecanismo | LLM asignados provisionalmente |
| C7 | Puertos y adaptadores locales | Cumple | Sustitución requiere migración |
| T1 | Traza, etapas y métricas | Cumple | Sin carga ni Prometheus |
| T2 | Feedback ligado a resultado/traza | Parcial | Sin muestra real ni reentrenamiento |
| B1 | Secciones 2–4 | Cubierto | Reservas expresas |
| B2 | Figuras 1–5 | Cubierto | — |
| B3 | Figuras 6–10 | Cubierto | — |
| B4 | Nueve ADR | Cubierto | ADR-07 permanece provisional por G1 |
| B5 | Sección 7 y corridas | Cubierto con brecha | G1 y revisión humana |
| B6 | Sección 10 | Cubierto con brecha | Métricas no evaluadas declaradas |
| B7 | Entregables, referencias y reproducción | Cubierto | Actualizar índice al abrir Word si procede |
