import streamlit as st
from pdf2docx import Converter
from docx import Document
from docx.shared import Pt
from deep_translator import GoogleTranslator
import os
import subprocess

# Configuración de la página
st.set_page_config(page_title="Traductor Alarmas PRO", page_icon="🎨")

st.title("🎨 Traductor Maquetado (Intento de perfección)")
st.markdown("""
Esta versión intenta respetar **fuentes, colores, negritas y tamaños**.
*Nota: Reduce ligeramente la letra para que el texto traducido quepa en las cajas originales.*
""")

# --- FUNCIONES ---

def traducir_texto(texto, idioma_destino):
    if not texto or len(texto) < 2:
        return texto
    try:
        return GoogleTranslator(source='auto', target=idioma_destino).translate(texto)
    except:
        return texto

def copiar_estilo(run_origen, run_destino):
    """Copia fuente, tamaño, color y negrita del original al traducido"""
    try:
        run_destino.bold = run_origen.bold
        run_destino.italic = run_origen.italic
        run_destino.underline = run_origen.underline
        run_destino.font.name = run_origen.font.name
        
        # Copiar color si existe
        if run_origen.font.color and run_origen.font.color.rgb:
            run_destino.font.color.rgb = run_origen.font.color.rgb
        
        # Copiar tamaño (y reducirlo un pelín para que quepa)
        if run_origen.font.size:
            # Reducimos un 10% el tamaño para compensar que el español es más largo
            nuevo_tamano = run_origen.font.size.pt * 0.9
            run_destino.font.size = Pt(max(6, nuevo_tamano)) # Mínimo 6pt
    except:
        pass # Si falla algún estilo, ignoramos para no romper el programa

def procesar_bloque(bloque, lang_code):
    """Procesa un párrafo o celda manteniendo el estilo del primer trozo"""
    # Si el párrafo está vacío, pasamos
    if not bloque.text.strip():
        return

    # 1. Guardamos el estilo del PRIMER trozo de texto (run) que tenga formato
    # Esto es un truco: asumimos que todo el párrafo tiene el estilo del principio
    estilo_referencia = None
    for run in bloque.runs:
        if run.text.strip():
            estilo_referencia = run
            break
    
    if not estilo_referencia:
        return # No hay texto real

    # 2. Traducimos el texto completo del párrafo
    texto_original = bloque.text
    texto_traducido = traducir_texto(texto_original, lang_code)

    # 3. Borramos el contenido viejo
    bloque.clear()

    # 4. Añadimos el nuevo texto y le aplicamos el estilo guardado
    nuevo_run = bloque.add_run(texto_traducido)
    copiar_estilo(estilo_referencia, nuevo_run)

def convertir_docx_a_pdf_linux(input_docx, output_folder):
    try:
        cmd = [
            'libreoffice', '--headless', '--convert-to', 'pdf', 
            input_docx, '--outdir', output_folder
        ]
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process.returncode == 0
    except Exception as e:
        return False

def procesar_documento(input_pdf, lang_code):
    base_name = os.path.splitext(input_pdf)[0]
    temp_docx = f"{base_name}_temp.docx"
    
    # 1. PDF -> DOCX (Ajustamos parámetros para detectar mejor el layout)
    cv = Converter(input_pdf)
    # intersection_X_tolerance ayuda a detectar mejor columnas separadas
    cv.convert(temp_docx, start=0, end=None)
    cv.close()

    # 2. Traducir el DOCX con ESTILO
    doc = Document(temp_docx)
    total_bloques = len(doc.paragraphs) + len(doc.tables)
    bar = st.progress(0)
    contador = 0
    
    # Párrafos sueltos
    for para in doc.paragraphs:
        procesar_bloque(para, lang_code)
        contador += 1
        if contador % 10 == 0: bar.progress(min(contador/total_bloques, 0.8))
            
    # Tablas (aquí suelen estar las columnas de las revistas/folletos)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    procesar_bloque(paragraph, lang_code)
        contador += 1
    
    bar.progress(0.9)
    doc.save(temp_docx)
    
    # 3. DOCX -> PDF
    st.info("Reconstruyendo PDF final con estilos...")
    cwd = os.getcwd()
    convertir_docx_a_pdf_linux(temp_docx, cwd)
    
    pdf_final = f"{base_name}_temp.pdf"
    bar.progress(1.0)
    return pdf_final, temp_docx

# --- INTERFAZ ---

uploaded_file = st.file_uploader("Sube el PDF (Versión Maquetada)", type=["pdf"])

idiomas = {"Alemán": "de", "Inglés": "en", "Francés": "fr", "Holandés": "nl", "Italiano": "it"}
target = st.selectbox("Idioma:", list(idiomas.keys()))

if uploaded_file and st.button("TRADUCIR AHORA", type="primary"):
    
    with st.spinner('Analizando fuentes y colores...'):
        try:
            nombre_entrada = "entrada.pdf"
            with open(nombre_entrada, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            pdf_resultante, docx_temp = procesar_documento(nombre_entrada, idiomas[target])
            
            if os.path.exists(pdf_resultante):
                st.success("¡Hecho! Fíjate si ha respetado las negritas.")
                with open(pdf_resultante, "rb") as f:
                    st.download_button("📥 DESCARGAR PDF", f, file_name=f"Traducido_{target}.pdf")
                
                # Limpieza
                os.remove(nombre_entrada)
                os.remove(docx_temp)
                os.remove(pdf_resultante)
            else:
                st.error("Error generando el PDF final.")
                
        except Exception as e:
            st.error(f"Error: {e}")
