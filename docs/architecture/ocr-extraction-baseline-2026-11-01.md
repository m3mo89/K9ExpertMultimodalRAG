# Baseline de extracción y política OCR — 2026-11-01

## Muestra medida

La medición usa `PDFKit` sobre `enciclopedia-perros-caza.pdf` y cuenta caracteres y tokens extraídos por página. Los números sirven para clasificar extracción, no para afirmar calidad semántica.

| Página física | Tipo observado | Caracteres | Tokens aproximados | Decisión inicial |
|---:|---|---:|---:|---|
| 2 | predominantemente gráfica | 1 | 1 | candidata a OCR, aunque puede no contener texto útil |
| 3 | predominantemente gráfica | 1 | 1 | candidata a OCR, aunque puede no contener texto útil |
| 5 | portada/índice y diseño mixto | 853 | 134 | extracción directa; no indexar como evidencia material por defecto |
| 27 | ficha morfológica densa | 3,036 | 544 | extracción directa |
| 29 | ficha de raza con imagen | 2,379 | 419 | extracción directa |
| 103 | ficha de raza con imagen | 1,541 | 263 | extracción directa |
| 106 | ficha de raza densa | 2,747 | 459 | extracción directa |
| 226 | sección de salud | 1,410 | 251 | extracción directa y etiqueta documental de seguridad |
| 236 | sección de alimentación/salud | 1,317 | 220 | extracción directa y etiqueta documental de seguridad |

## Política OCR inicial

Una página entra en OCR selectivo si cumple alguna condición:

1. Tiene menos de 40 caracteres no blancos, o menos de 8 tokens.
2. Tiene entre 40 y 160 caracteres no blancos y falla una comprobación de proporción de caracteres legibles configurable.
3. La extracción falla o el PDF informa una página de imagen sin capa de texto.

No se realizará OCR automáticamente a páginas de índice, portada o texto válido sólo por contener una imagen. El resultado de OCR se almacenará junto con idioma, motor, versión, resolución, duración y métricas de calidad; una página sin texto útil después de OCR se conservará como tal y no se inventará contenido.

## Dependencia pendiente

El host no tiene `tesseract` disponible. El adapter OCR y las pruebas de precisión quedan condicionados a instalar y versionar Tesseract con datos de idioma español durante la implementación de la tarea 5.3. La política anterior permite continuar con extracción directa sin bloquear la ingesta inicial.
