import streamlit as st
import deepl
import os
import subprocess

# Configuración de página
st.set_page_config(page_title="Traductor Alarmas PRO", page_icon="🛡️")

st.title("🛡️ Traductor Total (Compresión + Traducción)")
st.markdown("""
**Sistema Inteligente:**
1. Si el PDF es muy pesado, **lo comprime automáticamente**.
2. Lo envía a **DeepL Oficial** manteniendo el diseño.
3. Te entrega el resultado listo.
""")

# --- CONFIGURACIÓN CLAVE ---
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("API Key de DeepL:", type="password")

if not api_key:
    st.warning("👈 Pon la clave en la izquierda para arrancar.")
    st.stop()

# --- FUNCION DE COMPRESIÓN (La Magia) ---
def comprimir_pdf(input_path, output_path):
    """
    Usa Ghostscript para reducir el tamaño del PDF.
    Nivel /ebook = 150 dpi (Calidad media, tamaño bajo).
    """
    try:
        # El comando mágico de Linux para comprimir
        cmd = [
            'gs', 
            '-sDEVICE=pdfwrite', 
            '-dCompatibilityLevel=1.4', 
            '-dPDFSETTINGS=/ebook', # /screen (muy bajo), /ebook (medio), /printer (alto)
            '-dNOPAUSE', 
            '-dQUIET', 
            '-dBATCH', 
            f'-sOutputFile={output_path}', 
            input_path
        ]
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        return False

# --- PROCESO PRINCIPAL ---
try:
    translator = deepl.Translator(api_key)
    usage = translator.get_usage()
    if usage.character.limit > 0:
        porc = usage.character.count / usage.character.limit
        st.sidebar.progress(porc)
        st.sidebar.caption(f"Gastado: {usage.character.count} / {usage.character.limit}")

except deepl.AuthorizationException:
    st.sidebar.error("❌ Clave incorrecta.")
    st.stop()
except Exception:
    st.sidebar.error("Error conectando con DeepL.")
    st.stop()

uploaded_file = st.file_uploader("Sube tu PDF (Da igual el tamaño)", type=["pdf"])

idiomas = {
    "Alemán": "DE", "Inglés (UK)": "EN-GB", "Francés": "FR", 
    "Holandés": "NL", "Italiano": "IT", "Ruso": "RU", "Polaco": "PL"
}
target_lang_name = st.selectbox("Traducir al:", list(idiomas.keys()))

if uploaded_file and st.button("TRADUCIR AHORA", type="primary"):
    
    target_code = idiomas[target_lang_name]
    
    # Nombres de archivos temporales
    input_original = "original.pdf"
    input_comprimido = "comprimido.pdf"
    output_final = "traducido.pdf"
    
    # Barra de estado
    status = st.status("🚀 Iniciando motor...", expanded=True)
    
    try:
        # 1. Guardar el archivo subido
        with open(input_original, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Tamaño original
        size_mb = os.path.getsize(input_original) / (1024 * 1024)
        status.write(f"📄 Archivo recibido ({size_mb:.2f} MB).")
        
        archivo_a_enviar = input_original
        
        # 2. DECIDIR SI COMPRIMIR
        # Si pesa más de 9 MB, lo comprimimos (DeepL acepta hasta 10, dejamos margen)
        if size_mb > 9.0:
            status.write("🔨 El archivo es grande. Comprimiendo para que DeepL lo acepte...")
            exito = comprimir_pdf(input_original, input_comprimido)
            
            if exito:
                nuevo_size = os.path.getsize(input_comprimido) / (1024 * 1024)
                status.write(f"✅ ¡Compresión exitosa! Nuevo tamaño: {nuevo_size:.2f} MB")
                archivo_a_enviar = input_comprimido
            else:
                status.warning("⚠️ No se pudo comprimir. Intentando enviar original...")
        else:
            status.write("✅ Tamaño correcto. Enviando directo.")

        # 3. ENVIAR A DEEPL
        status.write("🌍 Enviando a Alemania para traducción oficial...")
        translator.translate_document_from_filepath(
            archivo_a_enviar,
            output_final,
            target_lang=target_code
        )
        
        status.update(label="¡Completado! 🎉", state="complete", expanded=False)
        st.success("¡Traducción lista!")
        
        # 4. BOTÓN DESCARGA
        with open(output_final, "rb") as f:
            st.download_button(
                label="📥 DESCARGAR PDF FINAL",
                data=f,
                file_name=f"Contrato_{target_code}.pdf",
                mime="application/pdf"
            )

        # Limpieza
        for f in [input_original, input_comprimido, output_final]:
            if os.path.exists(f):
                os.remove(f)

    except deepl.QuotaExceededException:
        status.update(label="Error de Cuota", state="error")
        st.error("Has superado el límite de caracteres mensual.")
    except deepl.AuthorizationException:
        status.update(label="Error de Clave", state="error")
        st.error("Clave API incorrecta.")
    except deepl.DocumentTranslationLimitExceeded: # Error específico de tamaño
         status.update(label="Archivo Demasiado Grande", state="error")
         st.error("Incluso comprimido, el archivo supera los 10MB. Es un PDF monstruoso.")
    except Exception as e:
        status.update(label="Error", state="error")
        st.error(f"Ocurrió un error: {e}")
