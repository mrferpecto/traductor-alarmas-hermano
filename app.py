import streamlit as st
from pdf2docx import Converter
from docx import Document
from deep_translator import GoogleTranslator
import os
import subprocess

# Configuración de la página
st.set_page_config(page_title="Traductor de Contratos", page_icon="📝")

st.title("📝 Traductor de Contratos (PDF a PDF)")
st.markdown("""
**Instrucciones:**
1. Sube el PDF original.
2. El sistema lo pasará a Word, lo traducirá (Google Translate) y lo volverá a convertir a PDF.
3. **Paciencia:** El proceso tarda unos segundos por página.
""")

# --- FUNCIONES ---

def traducir_texto(texto, idioma_destino):
    # Solo traducimos si hay texto real (más de 2 letras)
    if not texto or len(texto) < 2:
        return texto
    try:
        # Usamos el traductor gratuito de Google
        return GoogleTranslator(source='auto', target=idioma_destino).translate(texto)
    except:
        return texto

def convertir_docx_a_pdf_linux(input_docx, output_folder):
    # Esta función usa LibreOffice instalado en el servidor para convertir a PDF
    try:
        cmd = [
            'libreoffice', '--headless', '--convert-to', 'pdf', 
            input_docx, '--outdir', output_folder
        ]
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process.returncode == 0
    except Exception as e:
        st.error(f"Error convirtiendo a PDF: {e}")
        return False

def procesar_documento(input_pdf, lang_code):
    base_name = os.path.splitext(input_pdf)[0]
    temp_docx = f"{base_name}_temp.docx"
    
    # 1. PDF -> DOCX
    cv = Converter(input_pdf)
    cv.convert(temp_docx, start=0, end=None)
    cv.close()

    # 2. Traducir el DOCX
    doc = Document(temp_docx)
    total_bloques = len(doc.paragraphs) + len(doc.tables)
    
    # Barra de progreso
    bar = st.progress(0)
    st.write("Traduciendo texto...")
    contador = 0
    
    # Traducir párrafos
    for para in doc.paragraphs:
        if para.text.strip():
            para.text = traducir_texto(para.text, lang_code)
        contador += 1
        if contador % 10 == 0: 
            progreso = min(contador / total_bloques, 0.8)
            bar.progress(progreso)
            
    # Traducir tablas (Precios, condiciones, etc.)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if p.text.strip():
                        p.text = traducir_texto(p.text, lang_code)
        contador += 1
    
    bar.progress(0.9)
    doc.save(temp_docx)
    
    # 3. DOCX -> PDF
    st.write("Generando PDF final (esto usa LibreOffice)...")
    cwd = os.getcwd() # Carpeta actual
    convertir_docx_a_pdf_linux(temp_docx, cwd)
    
    # El archivo resultante tendrá el mismo nombre que el docx pero acabado en .pdf
    pdf_final = f"{base_name}_temp.pdf"
    
    bar.progress(1.0)
    return pdf_final, temp_docx

# --- INTERFAZ ---

uploaded_file = st.file_uploader("Sube aquí el contrato (PDF)", type=["pdf"])

idiomas = {
    "Alemán": "de",
    "Inglés": "en",
    "Francés": "fr",
    "Holandés": "nl",
    "Italiano": "it",
    "Ruso": "ru",
    "Rumano": "ro"
}

idioma_seleccionado = st.selectbox("Elegir idioma destino:", list(idiomas.keys()))

if uploaded_file and st.button("TRADUCIR AHORA", type="primary"):
    
    target_code = idiomas[idioma_seleccionado]
    
    with st.spinner('⏳ Procesando... Por favor no cierres la pestaña.'):
        try:
            # Guardamos el archivo subido temporalmente
            nombre_entrada = "entrada.pdf"
            with open(nombre_entrada, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Llamamos a la función mágica
            pdf_resultante, docx_temp = procesar_documento(nombre_entrada, target_code)
            
            # Verificamos si se creó el PDF
            if os.path.exists(pdf_resultante):
                st.success("¡Traducción completada!")
                
                # Botón de descarga
                with open(pdf_resultante, "rb") as f:
                    st.download_button(
                        label="📥 DESCARGAR PDF TRADUCIDO",
                        data=f,
                        file_name=f"Contrato_Traducido_{target_code}.pdf",
                        mime="application/pdf"
                    )
                
                # Limpieza (borrar archivos temporales)
                os.remove(nombre_entrada)
                os.remove(docx_temp)
                os.remove(pdf_resultante)
            else:
                st.error("Hubo un problema generando el PDF final. Inténtalo de nuevo.")
                
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
