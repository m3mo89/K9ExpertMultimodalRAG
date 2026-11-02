# Puertas de aceptación v1 — fijadas el 2026-11-01

Estas puertas se fijan **antes** de ejecutar los experimentos de modelos de lenguaje, embeddings y umbrales (tareas 8.2–8.4). La versión legible por máquina es `evaluation/gates/acceptance-gates-v1.json`. Ninguna puerta se relaja después de observar resultados: si un candidato no la supera, la decisión queda provisional y el informe declara la brecha.

## Datasets de medición

- RAG y citas: `evaluation/datasets/k9-reference-v2.json` (22 casos, 20 con evidencia esperada).
- Capas obligatorias: `evaluation/datasets/k9-rubric-v1.json` (BreedMatch, 11 entradas problemáticas y 10 normales, 10 pares de caché, 8 casos de router y 6 de agente).

Las etiquetas de ambos datasets se construyeron con asistencia de agente a partir del texto de las páginas (PyMuPDF). La firma humana sigue pendiente y se registra en la tarea 8.5.

## Puertas

| Id | Área | Métrica | Criterio | Obligatoria |
|---|---|---|---|---|
| G1 | Citas | Precisión de cita E2 | ≥ 0.80 | Sí |
| G2 | Recuperación | Recall@5 E2 | ≥ 0.75 | Sí |
| G3 | Recuperación | Hit@5 E2 (al menos una página esperada en el top 5) | ≥ 0.85 | Sí |
| G4 | Recuperación | MRR E2 | ≥ 0.60 | No |
| G5 | Abstención | Abstención correcta en casos sin respaldo o filtrados | = 1.0 | Sí |
| G6 | Abstención | Falsas abstenciones en casos con respaldo | ≤ 0.20 | Sí |
| G7 | Salida estructurada | Llamadas de generación con JSON válido y citas resolubles | ≥ 0.95 | Sí |
| G8 | Guardarraíles | Detección de entradas problemáticas | ≥ 0.90 | Sí |
| G9 | Guardarraíles | Bloqueo falso de entradas normales | ≤ 0.10 | Sí |
| G10 | Caché semántica | Reutilizaciones entre perfiles distintos | = 0 | Sí |
| G11 | Router | Exactitud de alias y motivo | = 1.0 | Sí |
| G12 | Agente | Terminación dentro del máximo de iteraciones | = 1.0 | Sí |
| G13 | Agente | Decisión final esperada | ≥ 0.80 | No |
| G14 | BreedMatch | Exactitud de hallazgos (`match`/`mismatch`/`not_documented`) | ≥ 0.80 | Sí |
| G15 | BreedMatch | Páginas citadas dentro de las esperadas | ≥ 0.80 | Sí |
| G16 | Latencia | p95 de consulta fundamentada E2 | ≤ 20 s | Sí |
| G17 | Latencia | p50 de consulta fundamentada E2 | ≤ 8 s | No |
| G18 | Recursos | Tamaño cargado de los modelos enrutados según `ollama ps` | ≤ 8 GB en total | Sí |

## Reglas

1. Una puerta obligatoria no superada impide declarar el requisito como cumplido en la matriz de trazabilidad.
2. Los umbrales de suficiencia y de caché semántica se calibran sólo con casos de desarrollo y se validan con casos retenidos (tarea 8.4).
3. Cada medición cita el manifiesto de ejecución (`evaluation/runs/*.json`), con versión de dataset, código, configuración, modelos y entorno.
4. G7 se mide como la fracción de casos E2 que llamaron al modelo y no terminaron en `unverified` ni en `model_output_invalid`.
5. G18 se mide en el Mac de entrega con `ollama ps` tras cargar los alias `simple`, `complex` y `fallback`.

## Reglas de calibración (fijadas antes de medir, tarea 8.4)

Las particiones se definen por identificador, sin mirar puntuaciones:

- **Suficiencia de evidencia.** Muestras: preguntas de `k9-reference-v2` (positivas si `expected_state = grounded`, negativas si no) más las preguntas del agente A5 y A6 y las entradas fuera de dominio G-P07 y G-P08 (negativas). Desarrollo: identificadores con número impar; retenidas: con número par. Regla: si en desarrollo la mayor puntuación máxima de una negativa es menor que la menor de una positiva, el umbral es el punto medio redondeado a 0.005; si se solapan, se conserva el umbral vigente (0.68) y se informa del solapamiento. Validación: falsas abstenciones y falsos aciertos en retenidas.
- **Caché semántica.** Pares de `k9-rubric-v1` (sección `cache`). Desarrollo: C3, C5, C7, C9; retenidos: C4, C6, C8, C10. Regla: el umbral es el menor múltiplo de 0.01 estrictamente mayor que la similitud de todo par «separate» de desarrollo que comparta partición, con un mínimo de 0.85; si ningún par de desarrollo comparte partición, se conserva 0.92. Validación: G10 (cero reutilizaciones indebidas) en retenidos y tasa de aciertos en paráfrasis.
- Un umbral calibrado sólo sustituye al configurado si la validación en retenidos supera las puertas; si no, se conserva el vigente y se declara provisional.
