# Baseline de embeddings locales — 2026-11-01

## Modelo y contrato probado

- Modelo instalado: `nomic-embed-text:latest`.
- Arquitectura reportada por Ollama: `nomic-bert`, 137M parámetros, contexto configurado de 8192 y vector de 768 dimensiones.
- API local probada: `POST /api/embed` con entradas múltiples.
- Prefijos evaluados: `search_query:` para la pregunta y `search_document:` para fragmentos indexados.

## Prueba de recuperación mínima

Se embebió la pregunta R1 de `retrieval-reference-v1.md` junto con seis candidatos: teckel, norsk elghund, basset hound, beagle, salud e higiene y alimentación. Se ordenaron por producto punto de vectores normalizados por el modelo.

| Rango | Candidato | Similitud |
|---:|---|---:|
| 1 | Fragmento de teckel (página 27, evidencia esperada de R1) | 0.723 |
| 2 | Fragmento de norsk elghund | 0.561 |
| 3 | Fragmento de beagle | 0.517 |
| 4 | Fragmento de alimentación | 0.516 |
| 5 | Fragmento de salud | 0.492 |
| 6 | Fragmento de basset hound | 0.487 |

El resultado confirma que el contrato de prefijos y dimensionalidad es funcional para el caso morfológico R1. No demuestra Recall@K ni MRR del corpus completo.

## Decisión provisional

`embedding-default` queda provisionalmente asignable a `nomic-embed-text:latest`, 768 dimensiones, normalización compatible con similitud de coseno/producto punto. El alias, dimensión, prefijo y versión deberán formar parte de cada snapshot de índice; no se mezclarán vectores incompatibles.

## Puertas pendientes

1. Automatizar R1–R10 contra fragmentos reales y reportar Recall@K y MRR.
2. Medir preguntas con filtros, términos exactos y abstención; una pregunta sin evidencia no se considera recuperada por similitud accidental.
3. Comparar otro modelo de embeddings sólo si el baseline no alcanza la puerta de recuperación definida después de construir el corpus real.
4. Validar rendimiento y almacenamiento en el índice vectorial persistente seleccionado.
