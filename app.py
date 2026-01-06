import streamlit as st
import deepl
import os

# Configuración de página
st.set_page_config(page_title="Traductor Oficial Alarmas", page_icon="🛡️")

st.title("🛡️ Traductor de Contratos (Calidad Original)")
st.markdown("""
Esta versión usa la **API Oficial de DeepL**.
El formato, las tablas, las fotos y las negritas se mantendrán **exactos** al original.
""")

# --- CONFIGURACIÓN DE LA CLAVE ---
st.sidebar.header("Configuración")
# Aviso: La clave suele acabar en :fx
api_key = st.sidebar.text_input("Pega tu API Key completa:", type="password", help="Ejemplo: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx")

if not api_key:
    st.warning("👈 Pega la clave API en el menú de la izquierda.")
    st.stop()

# --- PROCESO DE TRADUCCIÓN ---
try:
    translator = deepl.Translator(api_key)
    usage = translator.get_usage()
    if usage.character.limit > 0:
        porc = usage.character.count / usage.character.limit
        st.sidebar.progress(porc)
        st.sidebar.caption(f"Consumo: {usage.character.count} / {usage.character.limit}")

except deepl.AuthorizationException:
    st.sidebar.error("❌ La clave es incorrecta. Parece incompleta o mal copiada.")
    st.stop()
except Exception as e:
    st.sidebar.error(f"Error de conexión: {e}")
    st.stop()

# --- SUBIDA Y TRADUCCIÓN ---
uploaded_file = st.file_uploader("Sube el PDF del contrato", type=["pdf"])

idiomas = {
    "Alemán": "DE",
    "Inglés (UK)": "EN-GB",
    "Francés": "FR",
    "Holandés": "NL",
    "Italiano": "IT",
    "Ruso": "RU",
    "Polaco": "PL"
}
target_lang_name = st.selectbox("Traducir al:", list(idiomas.keys()))

if uploaded_file and st.button("TRADUCIR DOCUMENTO", type="primary"):
    
    target_code = idiomas[target_lang_name]
    
    with st.spinner('Enviando a DeepL... Manteniendo diseño original...'):
        try:
            input_filename = "entrada.pdf"
            output_filename = "salida.pdf"
            
            with open(input_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # TRADUCCIÓN
            translator.translate_document_from_filepath(
                input_filename,
                output_filename,
                target_lang=target_code
            )
            
            with open(output_filename, "rb") as f:
                st.success("✅ ¡Traducción perfecta completada!")
                st.download_button(
                    label="📥 DESCARGAR PDF TRADUCIDO",
                    data=f,
                    file_name=f"Contrato_Traducido_{target_code}.pdf",
                    mime="application/pdf"
                )
            
            os.remove(input_filename)
            os.remove(output_filename)

        # AQUÍ ESTABA EL ERROR ANTES, YA ESTÁ CORREGIDO:
        except deepl.QuotaExceededException:
            st.error("Has gastado el límite gratuito de caracteres de DeepL este mes.")
        except deepl.AuthorizationException:
            st.error("La clave API no es válida. Revisa que la has copiado entera.")
        except Exception as e:
            st.error(f"Error inesperado: {e}")
