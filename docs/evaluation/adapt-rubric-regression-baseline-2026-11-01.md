# Baseline de regresión para `adapt-k9-expert-to-rubric`

Fecha de captura: 1 de noviembre de 2026. Esta línea base se tomó antes de implementar el cambio y sin ejecutar migraciones ni escribir en `data/`.

## Verificaciones ejecutadas

| Área | Comando | Resultado |
|---|---|---|
| Backend y arquitectura | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider -q` | 81 pruebas aprobadas; 5 advertencias de tipos SWIG de terceros |
| Estilo backend | `.venv/bin/ruff check backend` | Aprobado |
| Tipos backend | `.venv/bin/mypy` | Aprobado en 40 archivos |
| Frontend unitario | `npm --prefix frontend test -- --run` | 23 pruebas aprobadas en 7 archivos |
| Lint frontend | `npm --prefix frontend run lint` | Sin errores; 2 advertencias preexistentes `set-state-in-effect` en `src/hooks.ts` |
| Build frontend | `npm --prefix frontend run build` | Aprobado |

Las pruebas backend incluyen contratos HTTP, reglas arquitectónicas, migraciones SQLite, ingesta, embeddings, índice vectorial, consultas, citas, feedback, observabilidad, publicación atómica, eliminación y recuperación. La suite frontend incluye cliente API y vistas de chat, biblioteca, administración, sistema y evidencia.

## Baseline de evaluación versionado

No se creó una corrida nueva para evitar modificar artefactos o datos de producción. Se conservaron como baseline los manifiestos existentes:

- E1: `evaluation/runs/20261101T235301Z-E1-c29f7a.json`, 10 casos, abstención correcta 1.0, tasa de abstención falsa 0.625 y p50 313 ms.
- E2: `evaluation/runs/20261101T235315Z-E2-ce2fd4.json`, 10 casos, Recall@5 0.8125, MRR 0.7917, precisión de citas 0.6125, abstención correcta 1.0 y p50 5.03 s.

La precisión de citas E2 permanece por debajo de la puerta 0.80 y no constituye cumplimiento. El cambio debe conservar o mejorar el resto de esta línea base y no puede relajar puertas después de observar resultados.

## Estado del árbol de trabajo

Antes de la implementación ya estaban sin seguimiento la nueva rúbrica PDF y el directorio del cambio OpenSpec. No se atribuyen al cambio otras modificaciones locales del usuario.
