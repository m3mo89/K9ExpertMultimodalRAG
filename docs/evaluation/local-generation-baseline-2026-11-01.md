# Baseline de generación local — 2026-11-01

## Entorno y método

- Hardware: Apple Silicon arm64; el requisito de diseño es 16 GB de memoria unificada. El sandbox no permitió leer `hw.memsize`, por lo que la capacidad no se vuelve a afirmar como una medición de esta ejecución.
- Runtime: Ollama local en `127.0.0.1`.
- Modelos instalados inspeccionados: `llama3.2:3b` (Q4_K_M) y `qwen3.5:2b` (mxfp8).
- Carga observada por `ollama ps` tras las pruebas: Llama 3.2, 2.6 GB, GPU/llamacpp; Qwen 3.5, 3.2 GB, GPU/MLX. Estas cifras son tamaño cargado informado por Ollama, no una medición completa de memoria unificada del proceso.
- Prompt de prueba: evidencia mínima sobre la morfología del teckel y la pregunta R1 de `retrieval-reference-v1.md`.
- Configuración de prueba: `stream=false`, `format=json`, `temperature=0`; para Qwen se envió `think=false`.

## Resultados observados

| Modelo | Salida JSON | Fidelidad básica a evidencia | Citas listas para contrato | Duración total | Duración de generación | Veredicto |
|---|---|---|---|---:|---:|---|
| `llama3.2:3b` | Sí con `format=json` | Sí: cráneo ligeramente convexo y tronco alargado | No: devolvió el texto de la evidencia, no un ID estable | 3.42 s | 1.39 s | Candidato primario provisional, exige postverificación de IDs |
| `qwen3.5:2b` | Sí sólo con `think=false` y `format=json` | Sí: reprodujo los rasgos esenciales | No: devolvió objetos de cita con esquema distinto | 2.95 s | 2.36 s | Candidato alternativo; exige desactivar razonamiento y normalizar salida |

La primera llamada de CLI sin `format=json` produjo una abstención incorrecta de Llama y razonamiento visible de Qwen. Por ello, el gateway deberá aplicar parámetros de formato y, para Qwen, desactivar explícitamente el modo de razonamiento cuando se use para respuestas estructuradas.

## Decisión provisional

Se configura `text-default` como alias pendiente de benchmark, inicialmente resoluble a `llama3.2:3b`; `qwen3.5:2b` queda como alternativa de evaluación. Ningún resultado autoriza confiar en citas emitidas por el modelo: la barrera de salida debe validar IDs de evidencia y rechazar o abstenerse ante citas no resolubles.

## Trabajo pendiente antes de congelar el alias

1. Ejecutar R1–R10 con contexto recuperado real y formato de salida definitivo.
2. Medir p50/p95, carga fría/caliente y memoria unificada mediante instrumentación de host permitida.
3. Evaluar español, abstención, discrepancias, contenido de salud y cumplimiento de IDs de evidencia.
4. Comparar al menos un modelo adicional sólo si el benchmark muestra que los instalados no superan las puertas de calidad.
