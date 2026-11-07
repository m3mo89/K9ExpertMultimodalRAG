"""Genera los entregables académicos editables de K9 BreedMatch."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches as DInches, Pt as DPt, RGBColor as DRGB

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/deliverables"
ASSETS = BASE / "assets"
FINAL = BASE / "final"
PREVIEW = BASE / "preview"
for p in (ASSETS, FINAL, PREVIEW):
    p.mkdir(parents=True, exist_ok=True)

NAVY = "13233A"; BLUE = "177E89"; TEAL = "35A7A0"; GOLD = "F4B942"; RED = "C84C4C"
LIGHT = "F4F7FA"; DARK = "15202B"; MUTED = "536471"; WHITE = "FFFFFF"

DIAGRAMS = [
    ("01-contexto", "Contexto", [("Cazador",.08,.50),("K9 BreedMatch",.40,.50),("Corpus",.76,.72),("Administrador",.76,.28)], [(0,1),(1,2),(3,1)]),
    ("02-contenedores", "Contenedores", [("React\n:5173",.05,.50),("FastAPI\n:8000",.29,.50),("Ollama\n:11434",.58,.76),("Chroma",.58,.50),("SQLite",.58,.24)], [(0,1),(1,2),(1,3),(1,4)]),
    ("03-capas", "Capas del servicio", [("C1 API",.05,.50),("C2 Orquestación",.22,.50),("C3 Guardrails",.42,.76),("C4 Caché",.42,.50),("C5 Contexto",.42,.24),("C6 Router/Gateway",.68,.62),("C7 Adaptadores",.68,.34)], [(0,1),(1,2),(1,3),(1,4),(2,5),(3,5),(4,5),(5,6)]),
    ("04-componentes", "Componentes", [("Pydantic/API",.04,.72),("Servicios\naplicación",.27,.72),("Retriever",.50,.72),("Router",.72,.72),("Repositorios",.27,.28),("Vector index",.50,.28),("Ollama gateway",.72,.28)], [(0,1),(1,2),(1,3),(1,4),(2,5),(3,6)]),
    ("05-despliegue", "Despliegue local", [("Navegador",.05,.50),("Vite :5173",.26,.50),("API :8000",.47,.50),("Ollama :11434",.70,.72),("Datos locales",.70,.28)], [(0,1),(1,2),(2,3),(2,4)]),
    ("06-ingesta", "Secuencia de ingesta", [("Web",.03,.50),("API",.19,.50),("Worker",.35,.50),("Extractor",.51,.72),("Embeddings",.51,.28),("Chroma",.70,.50),("Caché",.86,.50)], [(0,1),(1,2),(2,3),(2,4),(4,5),(5,6)]),
    ("07-consulta", "Consulta normal", [("Web",.03,.50),("API",.17,.50),("Guardrail",.31,.72),("Caché",.31,.28),("Retriever",.49,.50),("Router",.65,.72),("LLM",.65,.28),("Métricas",.83,.50)], [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7)]),
    ("08-cache", "Consulta desde caché", [("Web",.05,.50),("API",.25,.50),("Caché exacta",.48,.70),("Caché semántica",.48,.30),("Respuesta\ntrazada",.76,.50)], [(0,1),(1,2),(1,3),(2,4),(3,4)]),
    ("09-bloqueada", "Consulta bloqueada", [("Entrada",.05,.50),("API",.25,.50),("Guardrails",.47,.50),("Bloqueo seguro",.72,.70),("Traza",.72,.30)], [(0,1),(1,2),(2,3),(2,4)]),
    ("10-agente", "Ciclo de agente", [("Consulta",.03,.50),("Recuperar",.22,.50),("Evaluar\nevidencia",.42,.50),("Reformular",.62,.72),("Generar",.62,.28),("Respuesta",.83,.28)], [(0,1),(1,2),(2,3),(3,1),(2,4),(4,5)]),
]

def diagram(path: Path, title: str, nodes, edges) -> None:
    fig, ax = plt.subplots(figsize=(11,5.6), dpi=180); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
    fig.patch.set_facecolor("#F4F7FA"); ax.set_facecolor("#F4F7FA")
    ax.text(.03,.94,title,fontsize=22,fontweight="bold",color="#13233A",va="top")
    boxes=[]
    for label,x,y in nodes:
        w,h=.15,.15; box=FancyBboxPatch((x,y-h/2),w,h,boxstyle="round,pad=.015,rounding_size=.025",fc="#FFFFFF",ec="#177E89",lw=2)
        ax.add_patch(box); ax.text(x+w/2,y,label,ha="center",va="center",fontsize=10,color="#15202B",fontweight="bold"); boxes.append((x,y,w,h))
    for a,b in edges:
        x1,y1,w1,_=boxes[a]; x2,y2,_,_=boxes[b]
        arr=FancyArrowPatch((x1+w1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=14,lw=1.8,color="#35A7A0",connectionstyle="arc3,rad=.04")
        ax.add_patch(arr)
    ax.text(.97,.04,"Fuente: docs/architecture/diagrams.md",ha="right",fontsize=8,color="#536471")
    fig.savefig(path,bbox_inches="tight",facecolor=fig.get_facecolor()); plt.close(fig)

for slug,title,nodes,edges in DIAGRAMS: diagram(ASSETS/f"{slug}.png",title,nodes,edges)

def chart_models() -> None:
    fig,axs=plt.subplots(1,2,figsize=(11,4.8),dpi=180); fig.patch.set_facecolor("#F4F7FA")
    axs[0].bar(["Llama 3.2 3B","Qwen 3.5 2B"],[.634,.708],color=["#177E89","#35A7A0"]); axs[0].axhline(.8,color="#C84C4C",ls="--"); axs[0].set_ylim(0,1); axs[0].set_title("Precisión de citas (G1 = 0.80)")
    axs[1].bar(["Nomic","BGE-M3"],[.808,.825],color=["#177E89","#35A7A0"]); axs[1].set_ylim(.75,.85); axs[1].set_title("MRR de recuperación")
    for ax in axs: ax.grid(axis="y",alpha=.2); ax.spines[["top","right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(ASSETS/"modelos-comparacion.png",bbox_inches="tight",facecolor=fig.get_facecolor()); plt.close(fig)
chart_models()

def rgb(hexv): return RGBColor.from_string(hexv)
def add_bg(slide, color=NAVY):
    shp=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,Inches(13.333),Inches(7.5)); shp.fill.solid(); shp.fill.fore_color.rgb=rgb(color); shp.line.fill.background()
def textbox(slide,text,x,y,w,h,size=24,color=WHITE,bold=False,align=PP_ALIGN.LEFT):
    box=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)); tf=box.text_frame; tf.clear(); tf.word_wrap=True
    p=tf.paragraphs[0]; p.text=text; p.alignment=align
    for r in p.runs: r.font.name="Aptos"; r.font.size=Pt(size); r.font.bold=bold; r.font.color.rgb=rgb(color)
    return box
def title(slide,t,kicker=None):
    textbox(slide,t,.55,.38,12.1,.65,28,NAVY,True)
    if kicker: textbox(slide,kicker,.58,1.02,11.8,.35,11,BLUE,True)
    line=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.58),Inches(1.35),Inches(1.1),Inches(.07)); line.fill.solid(); line.fill.fore_color.rgb=rgb(GOLD); line.line.fill.background()
def notes(slide,text):
    try: slide.notes_slide.notes_text_frame.text=text
    except Exception: pass
def bullet_slide(prs,heading,bullets,kicker=None,img=None,note=""):
    s=prs.slides.add_slide(prs.slide_layouts[6]); add_bg(s,LIGHT); title(s,heading,kicker)
    w=7.0 if img else 11.7
    box=s.shapes.add_textbox(Inches(.75),Inches(1.65),Inches(w),Inches(5.2)); tf=box.text_frame; tf.clear(); tf.word_wrap=True
    for i,b in enumerate(bullets):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph(); p.text=b; p.level=0; p.space_after=Pt(15)
        for r in p.runs: r.font.name="Aptos"; r.font.size=Pt(22); r.font.color.rgb=rgb(DARK)
    if img: s.shapes.add_picture(str(img),Inches(7.95),Inches(1.65),width=Inches(4.7))
    notes(s,note); return s
def table_slide(prs,heading,headers,rows,note=""):
    s=prs.slides.add_slide(prs.slide_layouts[6]); add_bg(s,LIGHT); title(s,heading,"EVIDENCIA MEDIDA")
    tbl=s.shapes.add_table(len(rows)+1,len(headers),Inches(.7),Inches(1.7),Inches(11.95),Inches(4.7)).table
    for j,h in enumerate(headers):
        c=tbl.cell(0,j); c.text=h; c.fill.solid(); c.fill.fore_color.rgb=rgb(NAVY)
    for i,row in enumerate(rows,1):
        for j,val in enumerate(row):
            c=tbl.cell(i,j); c.text=str(val); c.fill.solid(); c.fill.fore_color.rgb=rgb(WHITE if i%2 else "E9F1F5")
            for p in c.text_frame.paragraphs:
                p.alignment=PP_ALIGN.CENTER
                for r in p.runs: r.font.name="Aptos"; r.font.size=Pt(15); r.font.color.rgb=rgb(WHITE if i==0 else DARK); r.font.bold=(i==0)
    notes(s,note); return s

prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
s=prs.slides.add_slide(prs.slide_layouts[6]); add_bg(s); textbox(s,"K9 BREEDMATCH",.65,.65,4,.35,13,GOLD,True); textbox(s,"Recomendación explicable\nde perros de caza",.65,1.35,8.8,1.65,38,WHITE,True); textbox(s,"Embeddings · RAG · arquitectura local en capas",.68,3.25,8.5,.5,20,"B9DDE2"); textbox(s,"[NOMBRE DEL ALUMNO]  ·  Tópicos selectos de arquitectura de software",.68,6.45,11.5,.4,14,WHITE); notes(s,"0:00–0:25. Preséntate y formula la tesis: no es un chatbot; entrega una decisión auditable.")
bullet_slide(prs,"Una decisión, no una conversación",["Usuario concreto: cazador que debe elegir una raza para una tarea.","Entrada: presa, modalidad de trabajo y terreno.","Salida: razas priorizadas, compatibilidad, cobertura y citas por página.","Valor: reducir una revisión experta extensa a una recomendación verificable."],"PROBLEMA Y PROPUESTA",note="0:25–1:20. Explica la prueba anti-chatbot: sin caja de chat el producto principal conserva todo su valor.")
bullet_slide(prs,"Experiencia guiada",["1  Perfil de caza en tres pasos","2  Comparación determinista y cobertura de evidencia","3  Recomendación con advertencias y fuentes","4  Retroalimentación ligada a la traza"],"FLUJO DEL USUARIO",ASSETS/"01-contexto.png",note="1:20–2:00. Distingue compatibilidad de cobertura: la falta de evidencia no cuenta a favor ni en contra.")
bullet_slide(prs,"Todo ocurre en la Mac",["React consume exclusivamente la API por HTTP.","FastAPI organiza la lógica y expone OpenAPI.","Ollama sirve LLM y embeddings sin nube.","Chroma almacena vectores; SQLite conserva trazas, caché y feedback."],"ARQUITECTURA LOCAL",ASSETS/"02-contenedores.png",note="2:00–3:00. Subraya R2 y R8: local y con frontera HTTP real.")
bullet_slide(prs,"Capas con responsabilidades verificables",["C1–C2: API y orquestación","C3–C4: guardrails y caché","C5–C6: contexto RAG, router y gateway","C7: adaptadores; T1/T2: observabilidad y feedback"],"C1–C7 · T1–T2",ASSETS/"03-capas.png",note="3:00–4:15. Recorre de arriba abajo; las capas inferiores no conocen a las superiores.")
bullet_slide(prs,"RAG: de 243 páginas a evidencia",["Extracción y fragmentación por página/sección.","786 fragmentos con metadatos y generación de índice atómica.","Top-k 6, máximo 2 fragmentos por sección.","Recall@5 0.925 · Hit@5 0.950 · MRR 0.808."],"CONSTRUCCIÓN DE CONTEXTO",ASSETS/"06-ingesta.png",note="4:15–5:10. Explica que cada cita conserva documento, página y sección.")
table_slide(prs,"Dos LLM, dos compromisos",["Criterio","Llama 3.2 3B","Qwen 3.5 2B"],[["Ruta","simple / fallback","complex"],["Citas","0.634","0.708"],["Salida estructurada","1.00","0.90"],["Falsas abstenciones","0.20","0.40"],["p50","5.08 s","3.68 s"],["Estado","provisional","provisional"]],"5:10–6:10. Ninguno supera G1=0.80. La ruta es una decisión de compromiso, no un ganador absoluto.")
table_slide(prs,"Embeddings: gana el equilibrio",["Criterio","Nomic","BGE-M3"],[["Dimensiones","768","1024"],["Recall@1","0.575","0.625"],["Recall@5","0.925","0.925"],["Hit@5","0.950","0.950"],["MRR","0.808","0.825"],["Tiempo embeddings","16.1 s","34.4 s"],["Tamaño","274 MB","1.2 GB"]],"6:10–7:10. Se mantiene Nomic: empate en las puertas finales, mitad de tiempo y cerca de una cuarta parte del tamaño.")
bullet_slide(prs,"Control antes, durante y después",["Entrada: inyección, dominio, datos sensibles y forma.","Caché exacta y semántica, umbral 0.85 e invalidación por snapshot.","Agente acotado: recuperar → evaluar → reformular (máx. 2).","Salida: formato, citas, contexto y respuesta segura."],"GUARDRAILS · CACHÉ · AGENTE",ASSETS/"10-agente.png",note="7:10–8:05. Señala que cada decisión queda en la traza.")
bullet_slide(prs,"Demostración local · 5 minutos",["0:00  Salud del sistema y perfil guiado","1:00  Recomendación, cobertura y cita","2:10  Repetición desde caché","2:45  Entrada bloqueada","3:20  Ciclo de agente y retroalimentación","4:20  Métricas y OpenAPI"],"RUTA PRINCIPAL",note="8:05–13:05. Ejecuta la demo. Plan B: capturas/video corto, pero aclara que la evaluación se hace sobre la ejecución viva.")
table_slide(prs,"Resultados por capa",["Componente","Resultado","Lectura"],[["Guardrails","1.0 / FP 0.0","cumple"],["Router","exactitud 1.0","cumple"],["Caché","13.3 s → 20 ms","observado"],["Agente","terminación 1.0","cumple"],["BreedMatch","orden/estado 1.0","cumple"],["Páginas citadas","0.93","cumple"]],"13:05–14:00. Separa resultados del producto principal de la precisión de citas del chat.")
bullet_slide(prs,"Lo que funciona y lo que falta",["Fortaleza: decisión determinista, fuentes, operación local y trazabilidad.","Pendiente: precisión de citas del chat < 0.80.","Pendiente: revisión humana, validación especialista y ensayo sin conexión.","Siguiente paso: ampliar dataset, revisar evidencia y medir concurrencia.","Una recomendación útil también debe poder explicar sus límites."],"CONCLUSIÓN",note="14:00–15:00. Cierra con la tesis. Prepárate para explicar por qué Nomic y por qué la puntuación es determinista.")
prs.save(FINAL/"K9-BreedMatch-Presentacion.pptx")

def set_repeat_table_header(row):
    trPr=row._tr.get_or_add_trPr(); el=OxmlElement('w:tblHeader'); el.set(qn('w:val'),'true'); trPr.append(el)
def page_number(paragraph):
    run=paragraph.add_run(); fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE'); run._r.addnext(fld)
def shade(cell,color):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),color); tcPr.append(shd)
def heading(doc,text,level=1): doc.add_heading(text,level=level)
def para(doc,text,bold_lead=None):
    p=doc.add_paragraph(); p.paragraph_format.space_after=DPt(6); p.paragraph_format.line_spacing=1.12
    if bold_lead and text.startswith(bold_lead): p.add_run(bold_lead).bold=True; p.add_run(text[len(bold_lead):])
    else: p.add_run(text)
    return p
def bullets(doc,items):
    for item in items: doc.add_paragraph(item,style="List Bullet")
def add_table(doc,headers,rows,widths=None):
    t=doc.add_table(rows=1,cols=len(headers)); t.style="Light Shading Accent 1"; t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for j,h in enumerate(headers): t.cell(0,j).text=h; shade(t.cell(0,j),NAVY)
    set_repeat_table_header(t.rows[0])
    for row in rows:
        cells=t.add_row().cells
        for j,v in enumerate(row): cells[j].text=str(v); cells[j].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
    return t
def figure(doc,filename,caption,width=6.6):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(str(ASSETS/filename),width=DInches(width))
    c=doc.add_paragraph(caption); c.style="Caption"; c.alignment=WD_ALIGN_PARAGRAPH.CENTER
def newpage(doc): doc.add_page_break()

doc=Document(); sec=doc.sections[0]; sec.top_margin=DInches(.65); sec.bottom_margin=DInches(.65); sec.left_margin=DInches(.78); sec.right_margin=DInches(.78)
styles=doc.styles; styles['Normal'].font.name='Aptos'; styles['Normal'].font.size=DPt(9.5); styles['Title'].font.name='Aptos Display'; styles['Title'].font.size=DPt(30); styles['Title'].font.color.rgb=DRGB.from_string(NAVY)
for name,size,color in [('Heading 1',18,NAVY),('Heading 2',13,BLUE),('Heading 3',11,TEAL)]: styles[name].font.name='Aptos Display'; styles[name].font.size=DPt(size); styles[name].font.color.rgb=DRGB.from_string(color)
for s in doc.sections:
    f=s.footer.paragraphs[0]; f.alignment=WD_ALIGN_PARAGRAPH.CENTER; f.add_run("K9 BreedMatch · Informe técnico · "); page_number(f)

p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run("K9 BREEDMATCH").bold=True
doc.add_paragraph("\n"); t=doc.add_heading("Arquitectura local en capas para la recomendación explicable de razas de perros de caza mediante embeddings y RAG",0); t.alignment=WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph("\n\n"); meta=doc.add_paragraph(); meta.alignment=WD_ALIGN_PARAGRAPH.CENTER; meta.add_run("[NOMBRE DEL ALUMNO]\n[INSTITUCIÓN]\nTópicos selectos de arquitectura de software · Unidad II\n[NOMBRE DEL DOCENTE]\n7 de noviembre de 2026")
doc.add_paragraph("\n\n"); q=doc.add_paragraph("Producto local · Decisión auditable · Evidencia por página"); q.alignment=WD_ALIGN_PARAGRAPH.CENTER
newpage(doc)
heading(doc,"Resumen ejecutivo",1)
para(doc,"K9 BreedMatch es un sistema local de apoyo a la decisión que recomienda razas de perros de caza a partir de la presa objetivo, la modalidad de trabajo y el terreno. En lugar de entregar una conversación abierta, produce razas priorizadas, compatibilidad determinista, cobertura de evidencia y citas verificables por página.")
para(doc,"La solución combina React, una API FastAPI organizada en capas, Ollama, Chroma y SQLite. Integra guardrails, caché exacta y semántica, enrutamiento de modelos, un ciclo acotado de agente, observabilidad y retroalimentación. Todo se ejecuta localmente y la aplicación web consume la API por HTTP.")
para(doc,"La evaluación de recuperación obtuvo Recall@5 de 0.925, Hit@5 de 0.950 y MRR de 0.808 con Nomic. BGE-M3 obtuvo el mismo Recall@5 e Hit@5 y MRR de 0.825, pero duplicó el tiempo de embeddings y cuadruplicó el tamaño del modelo; por ello se conserva Nomic. Persisten limitaciones en la precisión de citas del chat, revisión humana y validación experta.")
heading(doc,"Contenido",1)
for x in ["1. Idea del producto","2. Dominio y corpus","3. Requisitos y atributos de calidad","4. Arquitectura","5. Comportamiento","6. Selección de modelos y enrutamiento","7. Diseño de las capas","8. Registro de decisiones","9. Evaluación","10. Limitaciones, riesgos y trabajo futuro","11. Referencias","12. Anexos"]: doc.add_paragraph(x)
newpage(doc)
heading(doc,"1. Idea del producto",1); heading(doc,"1.1 Usuario, problema y momento de uso",2)
para(doc,"El usuario principal es un cazador que necesita seleccionar una raza para una combinación concreta de presa, modalidad de trabajo y terreno. La tarea exige consultar descripciones dispersas, reconciliar vocabulario y distinguir evidencia documentada de opiniones generales.")
heading(doc,"1.2 Resultado y propuesta de valor",2); bullets(doc,["Lista priorizada de razas, no una respuesta conversacional.","Compatibilidad calculada por una política determinista y versionada.","Cobertura que indica cuánto del perfil está documentado.","Citas a página y advertencias sobre evidencia insuficiente."])
heading(doc,"1.3 Originalidad y medición",2); para(doc,"El producto combina recomendación semántica, verificación documental y explicabilidad. Su valor se mide mediante calidad de recuperación, consistencia del orden, cobertura de evidencia, latencia, utilidad registrada y capacidad para abstenerse.")
figure(doc,"01-contexto.png","Figura 1. Contexto de uso de K9 BreedMatch.",6.4)
newpage(doc)
heading(doc,"2. Dominio y corpus",1); para(doc,"El dominio comprende razas de perros de caza y sus aptitudes documentadas. El corpus principal es Enciclopedia de los perros de caza, de Claudio De Giuliani, Editorial De Vecchi, 2019, ISBN 978-1-68325-599-4, con 243 páginas.")
add_table(doc,["Propiedad","Valor"],[["Formato","PDF"],["Páginas","243"],["Fragmentos línea base","786"],["Extracción","PyMuPDF; OCR registrado cuando aplica"],["Metadatos","documento, página, sección, raza"],["Uso","académico; permiso por confirmar"]])
para(doc,"El PDF tiene derechos de autor y no debe redistribuirse fuera de la entrega. Dieciséis páginas fotográficas o con poco texto quedaron marcadas como candidatas a OCR. La licencia o permiso de uso académico debe confirmarse antes de la entrega.")
heading(doc,"3. Requisitos y atributos de calidad",1)
add_table(doc,["Atributo","Medida o política"],[["Fundamentación","Toda recomendación muestra fuentes"],["Latencia","p50 y p95 por ruta; caché observada"],["Privacidad","Modelos y datos en loopback"],["Seguridad","Guardrails de entrada y salida"],["Reproducibilidad","README, dependencias, preflight"],["Recursos","Modelos compatibles con 16–18 GB"]])
newpage(doc)
heading(doc,"4. Arquitectura",1); para(doc,"La regla de dependencia es descendente: la API delega en la orquestación y las capas inferiores se acceden mediante interfaces. Observabilidad y retroalimentación son transversales.")
figure(doc,"02-contenedores.png","Figura 2. Vista de contenedores."); figure(doc,"03-capas.png","Figura 3. Capas C1–C7 y transversales T1–T2.")
newpage(doc); heading(doc,"4.1 Componentes",2); figure(doc,"04-componentes.png","Figura 4. Componentes principales e interfaces."); para(doc,"Los puertos desacoplan servicios de aplicación y adaptadores. Chroma puede sustituirse sin modificar la API o la política de recomendación; SQLite es la fuente de verdad operacional.")
newpage(doc); heading(doc,"4.2 Despliegue local",2); figure(doc,"05-despliegue.png","Figura 5. Despliegue en el equipo del estudiante."); add_table(doc,["Proceso","Puerto / recurso"],[["React/Vite","127.0.0.1:5173"],["FastAPI","127.0.0.1:8000"],["Ollama","127.0.0.1:11434"],["Chroma","persistencia local"],["SQLite","datos, caché, trazas, feedback"]])
newpage(doc)
heading(doc,"5. Comportamiento",1); heading(doc,"5.1 Ingesta",2); figure(doc,"06-ingesta.png","Figura 6. Secuencia de ingesta, embeddings, publicación e invalidación."); para(doc,"La publicación es atómica: se extrae, fragmenta, incrusta y construye una nueva generación antes de hacerla activa. El cambio de snapshot invalida las respuestas dependientes del corpus anterior.")
newpage(doc); heading(doc,"5.2 Consulta normal",2); figure(doc,"07-consulta.png","Figura 7. Recorrido de una consulta normal."); para(doc,"La consulta se valida, atraviesa guardrails, consulta caché, recupera evidencia, selecciona ruta y modelo, genera, verifica salida y registra métricas. La respuesta incluye fuentes, modelo, caché y traza.")
newpage(doc); heading(doc,"5.3 Consulta desde caché",2); figure(doc,"08-cache.png","Figura 8. Respuesta desde caché exacta o semántica."); para(doc,"La caché exacta usa una identidad estructural; la semántica compara embeddings dentro de la misma partición y exige similitud de 0.85. El snapshot participa en la identidad para evitar evidencia obsoleta.")
newpage(doc); heading(doc,"5.4 Consulta bloqueada",2); figure(doc,"09-bloqueada.png","Figura 9. Bloqueo de entrada y respuesta segura."); para(doc,"La cadena de entrada detecta inyección de instrucciones, fuera de dominio, datos sensibles y forma inválida. Un rechazo termina antes de recuperar o llamar al modelo y queda ligado a la traza.")
newpage(doc); heading(doc,"5.5 Ciclo de agente",2); figure(doc,"10-agente.png","Figura 10. Ciclo recuperar–evaluar–reformular."); para(doc,"Cuando la evidencia inicial es insuficiente, el orquestador conserva el dominio, reformula y recupera de nuevo. El ciclo termina tras un máximo de dos iteraciones; si persiste la insuficiencia, el sistema se abstiene.")
newpage(doc)
heading(doc,"6. Selección de modelos y enrutamiento",1); heading(doc,"6.1 Modelos de lenguaje",2)
add_table(doc,["Criterio","llama3.2:3b","qwen3.5:2b"],[["Parámetros / cuantización","3.2 B / Q4_K_M","2.2 B / MXFP8"],["Precisión de cita","0.634","0.708"],["Salida estructurada","1.00","0.90"],["Falsas abstenciones","0.20","0.40"],["p50 / p95","5.08 / 8.23 s","3.68 / 7.82 s"],["Memoria cargado","3.1 GB","4.7 GB"],["Licencia","Llama Community","Apache 2.0"]])
para(doc,"La asignación permanece provisional porque ningún modelo supera G1 = 0.80. Llama se usa en simple y fallback por consistencia; Qwen en complex por latencia y citas, sin permitir que el LLM altere la puntuación determinista.")
heading(doc,"6.2 Embeddings",2); add_table(doc,["Criterio","Nomic","BGE-M3"],[["Dimensiones","768","1024"],["Recall@1 / @3 / @5","0.575 / 0.925 / 0.925","0.625 / 0.900 / 0.925"],["Hit@5","0.950","0.950"],["MRR","0.808","0.825"],["Tiempo embeddings","16.1 s","34.4 s"],["Tamaño","274 MB","1.2 GB"]]); para(doc,"Se mantiene Nomic porque empata en Recall@5 e Hit@5, supera a BGE-M3 en Recall@3 y reduce tiempo y almacenamiento. Los umbrales de similitud no son transferibles entre modelos.")
newpage(doc)
heading(doc,"7. Diseño de las capas",1)
add_table(doc,["Capa","Responsabilidad","Evidencia"],[["C1 API","HTTP, esquemas, errores","FastAPI/OpenAPI"],["C2 Orquestación","flujo y agente","máx. 2 iteraciones"],["C3 Guardrails","entrada/salida","detección 1.0"],["C4 Caché","exacta/semántica","umbral 0.85"],["C5 Contexto","RAG y prompt","Recall@5 0.925"],["C6 Router/Gateway","ruta, timeout, fallback","router 1.0"],["C7 Acceso","adaptadores locales","puertos/interfaces"],["T1 Observabilidad","trazas y métricas","por capa"],["T2 Feedback","utilidad/comentario","ligado a traza"]])
heading(doc,"7.1 Políticas clave",2); bullets(doc,["Top-k 6 y máximo dos fragmentos por sección.","Router complex si hubo reformulación, >2 razas, >3 criterios o >6 fragmentos.","Timeout de 120 s, reintento transitorio y fallback exclusivamente local.","Puntuación y orden deterministas; narrativa opcional no altera la decisión."])
newpage(doc)
heading(doc,"8. Registro de decisiones de arquitectura",1)
add_table(doc,["ADR","Decisión","Estado / consecuencia"],[["01","Fragmentación por página y sección","Aceptada; citas directas"],["02","Router determinista simple/complex","Aceptada; auditable"],["03","Caché semántica 0.85","Aceptada con riesgo"],["04","Guardrails en código","Aceptada"],["05","Agente acotado","Aceptada"],["06","Chroma por generaciones + SQLite","Aceptada"],["07","Alias de LLM","Provisional: G1"],["08","Nomic frente a BGE-M3","Aceptada"],["09","Puntuación determinista","Aceptada"]])
para(doc,"Las alternativas descartadas incluyen un clasificador LLM para enrutamiento, un único modelo, umbrales compartidos entre embeddings, publicación no atómica y puntuación decidida por el modelo. El criterio común fue privilegiar auditabilidad, operación local y degradación segura.")
heading(doc,"8.1 Consecuencias transversales",2); bullets(doc,["La explicabilidad depende de conservar metadatos y versiones.","Cambiar embeddings exige una generación nueva y recalibrar umbrales.","El chat hereda la limitación de citas de los LLM; BreedMatch reduce impacto con lógica determinista.","La caché acelera, pero exige particiones e invalidación estrictas."])
newpage(doc)
heading(doc,"9. Evaluación",1)
add_table(doc,["Componente","Métrica","Resultado","Estado"],[["Recuperación","Recall@5 / Hit@5","0.925 / 0.950","cumple"],["Citas Llama","precisión","0.634","no cumple G1"],["Citas Qwen","precisión","0.708","no cumple G1"],["Guardrails","detección / FP","1.0 / 0.0","cumple"],["Router","exactitud","1.0","cumple"],["Caché","indebidas","0","cumple"],["Agente","terminación","1.0","cumple"],["BreedMatch","orden/estado/hallazgos","1.0","cumple"],["Citas BreedMatch","páginas esperadas","0.93","cumple"]])
figure(doc,"modelos-comparacion.png","Figura 11. Comparación de generación y recuperación.",6.5)
newpage(doc)
heading(doc,"9.1 Análisis de errores",2); para(doc,"La evaluación encontró falsos bloqueos en el guardrail de dominio, negaciones mal interpretadas, alcance incorrecto de «nunca» y sustitución de evidencia durante la reformulación. Las correcciones conservaron datasets y puertas para permitir comparación.")
para(doc,"El déficit principal permanece en precisión de citas del chat. Algunas páginas adyacentes son pertinentes pero no estaban etiquetadas como aceptables; otras respuestas contienen citas realmente irrelevantes o síntesis vacías. La revisión humana debe distinguir ambos casos sin relajar retrospectivamente la puerta.")
heading(doc,"9.2 Con y sin RAG",2); add_table(doc,["Indicador","Sin RAG","Con RAG"],[["Citas","ninguna","verificables"],["Abstención correcta","0.50","1.00"],["Falsas abstenciones","0.60","0.20"],["p50","0.53 s","5.08 s"]]); para(doc,"RAG aumenta latencia, pero reduce invenciones y mejora abstención. La caché recupera parte de ese costo: en el ensayo local la repetición bajó de 13.3 s a 20 ms; es una observación de ensayo, no un promedio del dataset.")
newpage(doc)
heading(doc,"10. Limitaciones, riesgos y trabajo futuro",1)
add_table(doc,["Limitación","Riesgo","Trabajo futuro"],[["Citas del chat < 0.80","fundamentación incorrecta","revisión humana y prompts"],["Sin validación especialista","recomendación inadecuada","evaluación independiente"],["Extracción automática","afirmaciones erróneas","muestreo y veto"],["Umbrales por modelo","abstención o pase incorrecto","calibración separada"],["Ensayo offline pendiente","falla en defensa","preflight y plan B"],["Corpus con derechos","redistribución indebida","confirmar permiso"]])
heading(doc,"10.1 Lineamientos éticos",2); bullets(doc,["Advertir que el contenido es generado y puede contener errores.","No presentar recomendaciones como consejo veterinario.","No incluir datos personales o sensibles en corpus y trazas.","Declarar el uso de asistentes de IA y revisar el contenido final."])
heading(doc,"10.2 Uso declarado de IA",2); para(doc,"Se utilizaron asistentes de IA para apoyar especificaciones, implementación, pruebas, borradores de ADR, diagramas, datasets y redacción de estos entregables. Las etiquetas asistidas requieren firma humana antes de presentarse como revisión independiente. El producto ejecutado no consume modelos en la nube.")
newpage(doc)
heading(doc,"11. Referencias",1)
for r in ["De Giuliani, C. (2019). Enciclopedia de los perros de caza. Editorial De Vecchi.","Proyecto integrador: producto inteligente en capas con modelos de lenguaje, embeddings y RAG. Unidad II, 2026.","Repositorio K9 Expert: README, diagramas, ADR, evaluación y matriz de trazabilidad.","Ollama. Documentación de ejecución local de modelos.","FastAPI, Chroma y React. Documentación de las tecnologías utilizadas."]: doc.add_paragraph(r)
heading(doc,"12. Anexos",1); heading(doc,"12.1 Reproducción",2); para(doc,"El README contiene instalación, descarga de modelos, ingesta, preflight, ejecución, API y pruebas. La documentación OpenAPI se sirve en http://127.0.0.1:8000/docs.")
heading(doc,"12.2 Evidencia y endpoints",2); add_table(doc,["Recurso","Ubicación"],[["Diagramas","docs/architecture/diagrams.md"],["ADR","docs/adr/"],["Evaluación","docs/evaluation/ y evaluation/runs/"],["Trazabilidad","docs/rubric/traceability.md"],["Operación","docs/operations/local-operations.md"],["API","/docs y /openapi.json"]])
heading(doc,"12.3 Datos por completar",2); bullets(doc,["Nombre del alumno, institución y docente.","Confirmación de permiso del corpus.","Firma de revisión humana y ficha aprobada.","Resultado del ensayo final sin conexión."])
doc.save(FINAL/"K9-BreedMatch-Informe-Tecnico.docx")
print(FINAL/"K9-BreedMatch-Presentacion.pptx"); print(FINAL/"K9-BreedMatch-Informe-Tecnico.docx")
