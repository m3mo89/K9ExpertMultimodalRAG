"""Genera la presentación de defensa alineada con la rúbrica, sin tocar el original."""
from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/deliverables/assets"
FINAL = ROOT / "docs/deliverables/final"
OUT = FINAL / "K9-BreedMatch-Presentacion-Rubrica.pptx"

NAVY="13233A"; BLUE="177E89"; TEAL="35A7A0"; GOLD="F4B942"; RED="C84C4C"
LIGHT="F4F7FA"; DARK="15202B"; MUTED="536471"; WHITE="FFFFFF"; PALE="E7F2F3"

def rgb(v): return RGBColor.from_string(v)
def rect(s,x,y,w,h,color,r=0.10,line=None):
    sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if r else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb=rgb(color)
    if line: sh.line.color.rgb=rgb(line)
    else: sh.line.fill.background()
    return sh
def text(s,value,x,y,w,h,size=18,color=DARK,bold=False,align=PP_ALIGN.LEFT):
    b=s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); f=b.text_frame; f.clear(); f.word_wrap=True
    p=f.paragraphs[0]; p.text=value; p.alignment=align
    for run in p.runs:
        run.font.name="Aptos"; run.font.size=Pt(size); run.font.bold=bold; run.font.color.rgb=rgb(color)
    return b
def bg(s,color=LIGHT): rect(s,0,0,13.333,7.5,color,0)
def header(s,title,kicker="RUTA PRINCIPAL",n=None):
    text(s,kicker,.55,.25,6,.25,10,BLUE,True)
    text(s,title,.55,.52,12.1,.55,27,NAVY,True)
    rect(s,.55,1.15,1.0,.055,GOLD,0)
    if n: text(s,str(n),12.35,.3,.4,.3,10,MUTED,True,PP_ALIGN.RIGHT)
def note(s,oral,evidence,transition,time):
    s.notes_slide.notes_text_frame.text=(f"ORAL · {oral}\nLECTURA · Recorre de izquierda a derecha o de arriba abajo según las flechas.\nDECISIÓN / TRADE-OFF · {evidence}\nTRANSICIÓN · {transition}\nTIEMPO · {time}")
def bullets(s,items,x=.75,y=1.55,w=11.8,h=5.3,size=21):
    b=s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); f=b.text_frame; f.clear(); f.word_wrap=True
    for i,item in enumerate(items):
        p=f.paragraphs[0] if i==0 else f.add_paragraph(); p.text=item; p.space_after=Pt(12)
        for r in p.runs: r.font.name="Aptos"; r.font.size=Pt(size); r.font.color.rgb=rgb(DARK)
    return b
def cards(s,items,y=1.65,h=4.55):
    gap=.18; x=.62; w=(12.1-gap*(len(items)-1))/len(items)
    for title_,body,color in items:
        rect(s,x,y,w,h,WHITE,line=color); rect(s,x,y,w,.12,color,0)
        text(s,title_,x+.18,y+.25,w-.36,.5,18,color,True)
        text(s,body,x+.18,y+.88,w-.36,h-1.05,15,DARK)
        x += w+gap
def table(s,headers,rows,y=1.55,h=4.9,widths=None,size=12):
    t=s.shapes.add_table(len(rows)+1,len(headers),Inches(.58),Inches(y),Inches(12.15),Inches(h)).table
    if widths:
        for i,w in enumerate(widths): t.columns[i].width=Inches(w)
    for j,v in enumerate(headers):
        c=t.cell(0,j); c.text=v; c.fill.solid(); c.fill.fore_color.rgb=rgb(NAVY)
    for i,row in enumerate(rows,1):
        for j,v in enumerate(row):
            c=t.cell(i,j); c.text=str(v); c.fill.solid(); c.fill.fore_color.rgb=rgb(WHITE if i%2 else "EAF1F4")
    for i,row in enumerate(t.rows):
        for c in row.cells:
            c.margin_left=Inches(.08); c.margin_right=Inches(.06); c.margin_top=Inches(.04); c.margin_bottom=Inches(.03)
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.name="Aptos"; r.font.size=Pt(size); r.font.bold=(i==0); r.font.color.rgb=rgb(WHITE if i==0 else DARK)
    return t
def picture_slide(prs,title_,asset,caption,kicker="APÉNDICE · DIAGRAMAS",n=None):
    s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,title_,kicker,n)
    s.shapes.add_picture(str(ASSETS/asset),Inches(.65),Inches(1.35),width=Inches(12.0),height=Inches(5.55))
    text(s,caption,.7,6.93,11.9,.25,9,MUTED)
    return s

prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)

# 1
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s,NAVY)
text(s,"K9 BREEDMATCH",.68,.62,4,.3,13,GOLD,True); text(s,"Decisión explicable\npara perros de caza",.68,1.35,8.8,1.55,38,WHITE,True)
text(s,"Arquitectura local · embeddings · RAG · evidencia por página",.72,3.15,10,.45,19,"B9DDE2")
text(s,"[NOMBRE DEL ALUMNO] · Tópicos selectos de arquitectura de software",.72,6.48,11.5,.3,13,WHITE)
note(s,"Tesis: BreedMatch transforma un perfil en una decisión auditable; el chat es secundario.","Producto más allá de chatbot; falta completar metadatos académicos.","Primero, el problema y la prueba anti-chatbot.","0:00–0:20")

# 2
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Una decisión, no una conversación","PROBLEMA · USUARIO · RESULTADO",2)
cards(s,[("Momento","Un cazador elige raza para una presa, modalidad y terreno concretos.",BLUE),("Resultado","Top de razas, compatibilidad, cobertura, conflictos y citas por página.",TEAL),("Prueba anti-chatbot","Sin chat, el motor determinista y la evidencia siguen resolviendo la tarea principal.",GOLD)])
text(s,"Caso conductor · venado + trabajo de rastro + monte · sólo valores admitidos por la aplicación",.78,6.55,11.7,.35,14,NAVY,True,PP_ALIGN.CENTER)
note(s,"Presenta al usuario y evita prometer una raza concreta antes de ejecutar el caso.","R12 cumple; la ficha docente sigue pendiente.","Veamos cómo el usuario llega a una respuesta verificable.","0:20–1:05")

#3
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"El valor se conserva sin el chat","FLUJO DEL PRODUCTO",3)
cards(s,[("1 · Perfil","Presa, función y terreno se traducen a dimensiones controladas.",BLUE),("2 · Decisión","Reglas versionadas calculan compatibilidad y orden; el LLM no cambia el ranking.",TEAL),("3 · Evidencia","Cobertura y citas distinguen lo documentado de lo desconocido.",GOLD),("4 · Mejora","Feedback queda ligado a traza, modelo y resultado.",RED)],h=4.3)
text(s,"Valor medible: consistencia del orden · cobertura · páginas esperadas · utilidad · latencia",.75,6.35,11.8,.4,15,NAVY,True,PP_ALIGN.CENTER)
note(s,"Distingue compatibilidad de cobertura: ausencia de evidencia no suma ni resta.","BreedMatch: orden/estado/hallazgos 1.0; páginas esperadas 0.93 en dataset acotado.","Ahora, de dónde sale la evidencia.","1:05–1:40")

#4 corpus
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Corpus propio, trazable y con límites","R1 · DOMINIO",4)
cards(s,[("243 páginas","Enciclopedia de los perros de caza · español · PDF.",BLUE),("786 fragmentos","Página, sección, documento y raza preservados en metadatos.",TEAL),("Condición de uso","Derechos de autor: no redistribuir. Permiso académico por confirmar.",RED)])
text(s,"Originalidad: unir decisión determinista + recuperación documental + explicación acotada",.75,6.35,11.8,.4,16,NAVY,True,PP_ALIGN.CENTER)
note(s,"Describe origen, tamaño, idioma y condición de uso sin presentar permiso como concedido.","README; dataset con SHA-256; corrida Nomic.","Con el producto definido, pasamos al mapa completo del sistema.","1:40–2:00")

#5 overview
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Cinco vistas responden cinco preguntas","ARQUITECTURA · MAPA DE VISTAS",5)
table(s,["Vista","Pregunta","Uso en defensa"],[["1 Contexto","¿Quién usa el sistema y qué queda fuera?","Producto"],["2 Contenedores","¿Qué procesos y almacenes colaboran?","Ruta principal"],["3 Capas","¿Dónde vive cada responsabilidad?","Ruta principal"],["4 Componentes","¿Qué módulos e interfaces realizan el trabajo?","Apéndice"],["5 Despliegue","¿Dónde corre y por qué es local?","Ruta principal"]],widths=[2.2,5.1,4.85],size=14)
note(s,"Explica que las vistas se complementan; contenedor C4 no significa Docker.","Los cinco diagramas están incluidos y numerados.","Empecemos por procesos, protocolos y almacenes.","2:00–2:20")

#6 containers
s=picture_slide(prs,"Contenedores: la web sólo conoce HTTP","02-contenedores.png","Figura 2 · React → FastAPI por HTTP; Ollama, Chroma, SQLite y archivos quedan detrás del servicio.","ARQUITECTURA · CONTENEDORES",6)
note(s,"Señala la frontera R8 y distingue web/API de recursos de infraestructura.","Puertos reales: 5173, 8000, 11434; worker de concurrencia 1.","Dentro del servicio, las responsabilidades no están mezcladas.","2:20–3:00")

#7 RAG prep
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"RAG empieza antes de la consulta","PREPARACIÓN · EMBEDDINGS",7)
cards(s,[("PDF","Extracción PyMuPDF; OCR sólo cuando aplica.",BLUE),("Fragmento","Unidad por página/sección con solapamiento lógico y metadatos.",TEAL),("Embedding","Vector numérico de significado; no genera texto.",GOLD),("Índice","Nomic 768d → Chroma; publicación por generación atómica.",RED)],h=4.15)
text(s,"Cambio de modelo ⇒ regenerar índice + recalibrar umbrales",.75,6.25,11.8,.45,17,NAVY,True,PP_ALIGN.CENTER)
note(s,"Aclara diferencia entre embedding y LLM. No inventes tamaño fijo: la política respeta página/sección.","ADR-01 y ADR-08; 786 fragmentos en la corrida Nomic.","En consulta, esos vectores seleccionan evidencia, no la respuesta.","3:00–3:40")

#8 query RAG
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Recuperar, decidir y sólo después redactar","CONSULTA · RAG",8)
cards(s,[("1 · Representar","Consulta → embedding con el mismo modelo del índice.",BLUE),("2 · Recuperar","k=6; máximo 2 fragmentos por sección; filtros inmutables.",TEAL),("3 · Decidir","Matcher determinista produce match / mismatch / no documentado.",GOLD),("4 · Redactar","Prompt usa hallazgos + evidence_ids; salida valida citas.",RED)],h=4.25)
text(s,"Evidencia insuficiente → reformular hasta 2 iteraciones o abstenerse",.75,6.30,11.8,.4,16,NAVY,True,PP_ALIGN.CENTER)
note(s,"Un fragmento conserva documento, página, sección y raza; las citas se verifican contra evidence_ids.","Umbral de suficiencia provisional; no afirmar justificación experimental completa.","Ahora recorremos el servicio capa por capa.","3:40–4:20")

#9 layers
s=picture_slide(prs,"Capas: dependencia estática ≠ orden de ejecución","03-capas.png","Figura 3 · C1–C7 dependen hacia abajo; T1/T2 cruzan el flujo. La secuencia temporal se muestra aparte.","ARQUITECTURA · CAPAS",9)
note(s,"Recorre C1 a C7 y luego T1/T2; recalca puertos e inversión de dependencias.","test_architecture.py comprueba fronteras; el dibujo simplifica llamadas internas.","El siguiente mapeo conecta nombres académicos con archivos reales.","4:20–4:55")

#10 mapping
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"La arquitectura existe en módulos reales","CAPAS → CÓDIGO",10)
table(s,["Capa","Módulos principales","Responsabilidad"],[["C1","presentation/api.py","HTTP, validación, OpenAPI"],["C2","query.py · breed_analysis.py · agent.py","orquestar y reformular"],["C3","guardrails.py · generation.py","entrada, salida, citas"],["C4","response_cache.py","exacta, semántica, TTL"],["C5","indexing.py · breed_match.py","recuperar, contexto, ranking"],["C6","routing.py · generation.py","ruta, gateway, fallback"],["C7","infrastructure/* · ports/*","SQLite, Chroma, Ollama, archivos"],["T1/T2","observability.py · interactions.py","traza, métricas, feedback"]],widths=[1.1,4.35,6.7],size=11)
note(s,"Da un ejemplo de dirección: API conoce un puerto; el adaptador no conoce FastAPI.","La composición conecta implementaciones; no todos los nombres coinciden literalmente con carpetas C1–C7.","Con la estructura clara, vemos el comportamiento normal.","4:55–5:00")

#11 main sequence
s=picture_slide(prs,"Solicitud normal: diez pasos observables","07-consulta.png","Figura 7 · Validar → trazar → guardrails → caché → recuperar → enrutar → generar → validar → persistir → feedback.","COMPORTAMIENTO · CONSULTA",11)
note(s,"La figura resume; en el apéndice está la secuencia UML completa con actor y participantes.","El ranking ocurre antes del LLM; la narrativa no puede alterarlo.","Esa separación permite comparar modelos sin cambiar la decisión.","5:00–5:25")

#12 models
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Dos LLM: ninguno gana todo","SELECCIÓN DE MODELOS",12)
table(s,["Criterio","Llama 3.2 3B","Qwen 3.5 2B"],[["Ruta","simple / fallback","complex"],["Precisión de citas","0.634","0.708"],["Salida estructurada","1.00","0.90"],["Falsas abstenciones","0.20","0.40"],["p50 / p95","5.08 / 8.23 s","3.68 / 7.82 s"],["Memoria / cuantización","3.1 GB · Q4_K_M","4.7 GB · MXFP8"],["Licencia","Llama Community","Apache 2.0"],["Estado","provisional: G1 < 0.80","provisional: G1 < 0.80"]],widths=[3.6,4.25,4.3],size=12)
note(s,"Mismo corpus y preguntas E2. Qwen mejora citas/latencia; Llama estructura y se abstiene menos.","No hay ganador absoluto ni revisión humana firmada.","La comparación de embeddings produce otra decisión.","5:25–6:05")

#13 embeddings
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Nomic gana por equilibrio, no por MRR","SELECCIÓN DE EMBEDDINGS",13)
table(s,["Criterio","Nomic","BGE-M3"],[["Dimensiones","768","1024"],["Recall@1 / @3 / @5",".575 / .925 / .925",".625 / .900 / .925"],["Hit@5 / MRR",".950 / .808",".950 / .825"],["Embeddings del corpus","16.1 s","34.4 s"],["Tamaño","274 MB","1.2 GB"],["Decisión","activo","alternativa medida"]],widths=[4.0,4.05,4.1],size=14)
text(s,"Beneficio: mismo Recall@5/Hit@5 con menor costo · Sacrificio: −0.017 MRR y −0.050 Recall@1",.72,6.45,11.9,.35,13,NAVY,True,PP_ALIGN.CENTER)
note(s,"Define Recall@k como recuperación de evidencia esperada; no lo llames precisión del sistema.","BGE-M3 no usa el umbral Nomic sin recalibración; regenerar índice tiene costo.","Ahora, controles y degradación segura.","6:05–6:45")

#14 controls
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Control antes, durante y después","GUARDRAILS · CACHÉ · GATEWAY",14)
cards(s,[("Entrada","Inyección, dominio, datos sensibles y forma. Bloquea antes de recuperar/generar.",BLUE),("Caché","Exacta + semántica 0.85; TTL y snapshot. Revalida la salida reutilizada.",TEAL),("Gateway","Timeout 120 s, reintento transitorio y fallback local configurado.",GOLD),("Salida","Esquema, razas y evidence_ids; responder seguro si falla.",RED)],h=4.2)
text(s,"Riesgo residual: falsos positivos/negativos y reutilización semántica incorrecta fuera del dataset",.7,6.35,11.95,.35,14,NAVY,True,PP_ALIGN.CENTER)
note(s,"No confundas fallback con router: el router selecciona antes; fallback responde a una falla.","Guardrails 1.0/FP 0.0 y caché sin reutilización indebida en conjunto acotado.","Si la recuperación es débil, entra un ciclo acotado.","6:45–7:20")

#15 agent
s=picture_slide(prs,"Agente: un ciclo con condición terminal","10-agente.png","Figura 10 · Recuperar → evaluar → reformular → recuperar; máx. 2. Si sigue débil, abstención sin generación.","ORQUESTACIÓN · AGENTE",15)
note(s,"Una llamada aislada no es agente: muestra estado, herramienta, evaluación, límite y terminación.","Terminación 1.0; G13 no obligatoria 0.67 en casos originales.","Con esto, pasamos a la demostración de cinco minutos.","7:20–8:00")

#16 demo
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Demostración local · 5 minutos","RUTA REPRODUCIBLE",16)
table(s,["Tiempo","Acción","Señal observable"],[["0:00","salud + cargar PDF pequeño","job available + invalidación"],["1:05","BreedMatch con venado/monte","ranking + citas + trace_id"],["2:05","repetir + paráfrasis","exact hit + semantic hit"],["2:45","inyección","rejected; generation=false"],["3:05","evidencia débil","iteración o abstención"],["3:40","feedback + métricas","vínculo a traza y capas"],["4:35","OpenAPI","frontera `/api/v1`"]],widths=[1.3,4.7,6.15],size=13)
note(s,"Ejecuta el guion; si una ruta no se activa, no la fuerces ni la declares exitosa.","Plan B: capturas/video del mismo ensayo; no sustituye la demo viva.","Después de la demo, interpretamos resultados y límites.","8:00–13:00")

#17 eval
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Resultados por capa, no una sola precisión","EVALUACIÓN",17)
table(s,["Capa","Métrica","Resultado","Lectura"],[["Recuperación","Recall@5 / Hit@5",".925 / .950","cumple"],["Chat Llama / Qwen","precisión de citas",".634 / .708","no cumple G1"],["Guardrails","detección / FP","1.0 / 0.0","dataset acotado"],["Router","exactitud","1.0","dataset etiquetado"],["Caché","reuso indebido","0","casos repetidos/paráfrasis"],["Agente","terminación","1.0","máx. 2"],["BreedMatch","páginas esperadas",".93","producto principal"]],widths=[2.25,3.2,2.4,4.3],size=11)
note(s,"Explica cada métrica antes de interpretarla; los 1.0 no prueban generalización.","Datasets y puertas están versionados; revisión humana pendiente.","La comparación con/sin RAG muestra el costo del fundamento.","13:00–13:45")

#18 tradeoffs
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"El diseño gana auditabilidad y paga latencia","TRADE-OFFS",18)
cards(s,[("RAG","+ citas y abstención\n− p50 5.08 s vs 0.53 s sin RAG",BLUE),("Local","+ privacidad y costo marginal\n− recursos y arranque",TEAL),("Determinista","+ reproducibilidad\n− vocabulario controlado",GOLD),("Caché","+ 13.3 s → 20 ms observado\n− riesgo de reuso incorrecto",RED)],h=4.25)
text(s,"Observación de caché ≠ promedio del dataset · comparación conceptual ≠ alternativa experimentada",.75,6.35,11.8,.35,14,NAVY,True,PP_ALIGN.CENTER)
note(s,"Distingue mediciones de decisiones conceptuales; no atribuyas causalidad más allá del ensayo.","ADR-01…09 documentan contexto, alternativas y consecuencias.","Cerramos con límites que condicionan la conclusión.","13:45–14:20")

#19 conclusion
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s,NAVY); text(s,"Conclusión",.7,.55,4,.5,14,GOLD,True)
text(s,"Una recomendación útil\ntambién explica sus límites.",.7,1.25,11.7,1.2,36,WHITE,True)
cards(s,[("Demostrado","Decisión determinista, arquitectura local, evidencia por página y trazas.",BLUE),("No demostrado","G1 del chat, validación especialista, revisión humana y ensayo offline final.",RED),("Siguiente","Ampliar dataset, firmar revisión, calibrar por modelo y probar clon limpio.",GOLD)],y=3.15,h=2.6)
note(s,"Vuelve a la tesis y declara brechas sin minimizarlas.","La presentación sintetiza el informe; no sustituye R11 ni la evidencia versionada.","Abrimos preguntas; el apéndice contiene diagramas, ADR, API y trazas.","14:20–15:00")

# Appendix 20–34
for i,(title_,asset,cap) in enumerate([
    ("Contexto: usuarios y frontera externa","01-contexto.png","Figura 1 · El registro de Ollama sólo participa al instalar; no en tiempo de ejecución."),
    ("Componentes e interfaces","04-componentes.png","Figura 4 · La composición conecta servicios, puertos y adaptadores."),
    ("Despliegue local y recursos","05-despliegue.png","Figura 5 · Mac Apple Silicon 16–18 GB; procesos 5173/8000/11434 y datos locales."),
    ("Secuencia de ingesta","06-ingesta.png","Figura 6 · Extraer → fragmentar → incrustar → validar → publicar → invalidar caché."),
    ("Secuencia desde caché semántica","08-cache.png","Figura 8 · Misma partición/snapshot, coseno ≥0.85 y funciones controladas idénticas."),
    ("Secuencia bloqueada por guardrail","09-bloqueada.png","Figura 9 · Rechazo antes de recuperación o modelo; la traza conserva el motivo."),
],20):
    s=picture_slide(prs,title_,asset,cap,"APÉNDICE · DIAGRAMA OBLIGATORIO",i); note(s,"Usa sólo si la pregunta exige detalle.","Fuente editable: K9-BreedMatch-Diagramas-Editables.md.","Regresa a la decisión o evidencia relacionada.","Q&A")

s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Seis ADR que sostienen la defensa","APÉNDICE · DECISIONES",26)
table(s,["ADR","Decisión","Alternativa / costo residual"],[["01","página + sección + metadatos","chunk fijo; umbral provisional"],["02","router determinista","clasificador LLM; reglas requieren mantenimiento"],["03","caché semántica 0.85","sólo exacta; riesgo de margen"],["04","guardrails en código","moderador LLM; OOD no cubierto"],["05","agente máx. 2","bucle abierto; puede abstenerse antes"],["07/08","Llama/Qwen + Nomic","elección LLM provisional; regenerar índice"]],widths=[1.3,5.1,5.75],size=12)
note(s,"Para cada ADR: contexto, decisión, alternativa, evidencia y consecuencia.","Alternativas evaluadas y conceptuales deben distinguirse.","La siguiente lámina completa API y observabilidad.","Q&A")

s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"API: funciones mínimas y endpoints reales","APÉNDICE · API / WEB",27)
table(s,["Función","Endpoint"],[["Salud","GET /health"],["Carga / lista / elimina","POST/GET/DELETE /api/v1/documents…"],["Función principal","POST /api/v1/breed-analyses"],["Chat fundamentado","POST /api/v1/queries"],["Feedback","POST /breed-analyses/{id}/feedback"],["Métricas","GET /api/v1/admin/metrics"],["Configuración","GET /api/v1/configuration"],["Contrato","GET /openapi.json · /docs"]],widths=[4.2,7.95],size=13)
note(s,"Los nombres pueden diferir de la rúbrica; importa la cobertura del contrato.","La web usa `/api/v1`; no accede Ollama/Chroma.","Ahora, qué contiene una traza defendible.","Q&A")

s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Una traza explica qué pasó sin exponer texto","APÉNDICE · OBSERVABILIDAD",28)
cards(s,[("Identidad","trace_id · analysis_id · snapshot · versiones",BLUE),("Decisiones","guardrail · cache_hit · ruta · modelo · fallback",TEAL),("Costos","latencia total y por capa · iteraciones",GOLD),("Aprendizaje","útil/no útil + comentario ligado a la traza",RED)],h=4.2)
text(s,"Evidencia: TraceRecorder + repositorio SQLite + `/admin/metrics`; falta análisis longitudinal de feedback real",.75,6.35,11.8,.35,14,NAVY,True,PP_ALIGN.CENTER)
note(s,"Anonimiza: muestra ids y decisiones, no consulta completa ni secretos.","T1 cumple; T2 es parcial por uso en evaluación.","Las preguntas difíciles se responden con límites explícitos.","Q&A")

s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Preguntas previsibles de defensa","APÉNDICE · Q&A",29)
table(s,["Pregunta","Respuesta respaldada"],[["¿Por qué no dejar el ranking al LLM?","La política determinista es reproducible; el LLM sólo redacta."],["¿Por qué Nomic si BGE-M3 tiene mejor MRR?","Empata puertas finales, tarda menos de la mitad y ocupa ~¼."],["¿Un 1.0 significa resuelto?","No; describe un dataset acotado, no generalización."],["¿Por qué dos modelos?","Router/fallback separan complejidad y resiliencia; elección provisional."],["¿Qué ocurre sin evidencia?","Reformula hasta 2; después se abstiene."],["¿Es realmente offline?","Arquitectura local; ensayo desconectado final aún pendiente."]],widths=[4.1,8.05],size=12)
note(s,"Responde con evidencia y límites; evita convertir pendientes en funcionalidades.","Matriz completa: K9-BreedMatch-Cobertura-Rubrica.md.","Si piden detalle, abre informe/ADR/corrida concreta.","Q&A")

s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s); header(s,"Fuentes de evidencia y estado final","APÉNDICE · TRAZABILIDAD",30)
bullets(s,["Norma: docs/references/Proyecto_integrador_RAG.pdf","Arquitectura: docs/architecture/diagrams.md · pruebas de fronteras","Decisiones: docs/adr/ADR-01…09","Evaluación: evaluation/runs/ · datasets/ · acceptance-gates-v1","Informe: K9-BreedMatch-Informe-Tecnico.pdf","Brechas: G1, revisión humana, especialista, permiso de corpus, offline y clon limpio"],size=18)
note(s,"Aclara que una diapositiva no sustituye un entregable B.","Todos los números deben poder rastrearse a un archivo versionado.","Fin.","Q&A")

prs.save(OUT)
print(OUT)
