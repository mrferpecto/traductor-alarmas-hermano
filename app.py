import streamlit as st
from pdf2docx import Converter
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH # Importante para justificar
from deep_translator import GoogleTranslator
import os
import subprocess
import re

# Configuración de la página
st.set_page_config(page_title="Traductor Alarmas PRO", page_icon="⚖️")

st.title("⚖️ Traductor Contratos (Formato Justificado)")
st.markdown("""
**Mejoras V4:**
* Texto **Justificado** (alineado a ambos lados).
* Tamaño de letra original (sin reducciones).
* Corrección de palabras cortadas.
""")

# --- FUNCIONES ---

def traducir_texto(texto, idioma_destino):
    if not texto or len(texto) < 2:
        return texto
    
    # Limpieza previa: A veces los PDF traen palabras cortadas tipo "advan- ceds"
    # Intentamos quitar guiones de final de línea si parecen errores
    texto_limpio = texto.replace('-\n', '').replace('¬\n', '')
    
    try:
        return GoogleTranslator(source='auto', target=idioma_destino).translate(texto_limpio)
    except:
        return texto

def copiar_estilo(run_origen, run_destino):
    """Copia el estilo visual exacto del original"""
    try:
        run_destino.bold = run_origen.bold
        run_destino.italic = run_origen.italic
        run_destino.underline = run_origen.underline
        run_destino.font.name = run_origen.font.name
        
        # Color
        if run_origen.font.color and run_origen.font.color.rgb:
            run_destino.font.color.rgb = run_origen.font.color.rgb
        
        # Tamaño: LO DEJAMOS IGUAL (Quitamos la reducción del 10% anterior)
        if run_origen.font.size:
            run_destino.font.size = run_origen.font.size
            
    except:
        pass

def procesar_bloque(bloque, lang_code):
    """Procesa párrafo aplicando justificación"""
    if not bloque.text.strip():
        return

    # 1. Capturar estilo del primer trozo
    estilo_referencia = None
    for run in bloque.runs:
        if run.text.strip():
            estilo_referencia = run
            break
    
    if not estilo_referencia:
        return

    # 2. Traducir
    texto_original = bloque.text
    texto_traducido = traducir_texto(texto_original, lang_code)

    # 3. Reemplazar contenido
    bloque.clear()
    nuevo_run = bloque.add_run(texto_traducido)
    
    # 4. Aplicar estilo original
    copiar_estilo(estilo_referencia, nuevo_run)
    
    # 5. --- MAGIA NUEVA: JUSTIFICAR EL TEXTO ---
    # Esto obliga a que el texto se estire de izquierda a derecha
    bloque.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

def procesar_documento(input_pdf, lang_code):
    base_name = os.path.splitext(input_pdf)[0]
    temp_docx = f"{base_name}_temp.docx"
    
    # 1. PDF -> DOCX
    cv = Converter(input_pdf)
    # intersection_X_tolerance: Ayuda a que no cree cajas de texto demasiado estrechas
    cv.convert(temp_docx, start=0, end=None)
    cv.close()

    # 2. Traducir el DOCX
    doc = Document(temp_docx)
    total_bloques = len(doc.paragraphs) + len(doc.tables)
    bar = st.progress(0)
    contador = 0
    
    # Párrafos
    for para in doc.paragraphs:
        procesar_bloque(para, lang_code)
        contador += 1
        if contador % 10 == 0: bar.progress(min(contador/total_bloques, 0.8))
            
    # Tablas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    procesar_bloque(paragraph, lang_code)
        contador += 1
    
    bar.progress(0.9)
    doc.save(temp_docx)
    
    # 3. DOCX -> PDF con LibreOffice
    st.info("Generando PDF justificado y limpio...")
    cwd = os.getcwd()
    
    # Usamos subprocess para llamar a LibreOffice
    cmd = ['libreoffice', '--headless', '--convert-to', 'pdf', temp_docx, '--outdir', cwd]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    pdf_final = f"{base_name}_temp.pdf"
    bar.progress(1.0)
    
    return pdf_final, temp_docx

# --- INTERFAZ ---

uploaded_file = st.file_uploader("Sube el PDF (Versión V4 Justificada)", type=["pdf"])

idiomas = {"Alemán": "de", "Inglés": "en", "Francés": "fr", "Holandés": "nl", "Italiano": "it"}
target = st.selectbox("Idioma:", list(idiomas.keys()))

if uploaded_file and st.button("TRADUCIR", type="primary"):
    
    with st.spinner('Traduciendo y justificando textos...'):
        try:
            nombre_entrada = "entrada.pdf"
            with open(nombre_entrada, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            pdf_resultante, docx_temp = procesar_documento(nombre_entrada, idiomas[target])
            
            if os.path.exists(pdf_resultante):
                st.success("¡Traducción completada!")
                with open(pdf_resultante, "rb") as f:
                    st.download_button("📥 DESCARGAR PDF", f, file_name=f"Traducido_{target}.pdf")
                
                # Limpieza
                try:
                    os.remove(nombre_entrada)
                    os.remove(docx_temp)
                    os.remove(pdf_resultante)
                except:
                    pass
            else:
                st.error("Error al generar el archivo final.")
                
        except Exception as e:
            st.error(f"Error: {e}")
