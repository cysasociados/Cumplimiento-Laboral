import streamlit as st
import requests

# --- CONFIGURACIÓN ---
# ⚠️ PEGA AQUÍ TU NUEVA URL ENTRE LAS COMILLAS
URL_APPS_SCRIPT = "https://script.google.com/macros/library/d/1QS-c-O4GdV1OW5wuQaav4B2zfB8e0l9F5fEwaoUj8xqSkeFUyc62CrjW/1"

ID_CARPETA_TOLEDO = "11UQVAgZhkaCjt7BUofsjPcf_HybC-Qi6"
NOMBRE_ARCHIVO = "Certificado.122025.pdf"

st.set_page_config(page_title="Portal Auditoría", page_icon="🛡️")
st.title("🛡️ Portal de Auditoría Laboral")

st.info(f"📁 Buscando: `{NOMBRE_ARCHIVO}`")

if st.button("🚀 Consultar Documento"):
    with st.spinner("Conectando con Google Cloud..."):
        try:
            # Enviamos la consulta
            res = requests.get(URL_APPS_SCRIPT, params={
                "nombre": NOMBRE_ARCHIVO,
                "carpeta": ID_CARPETA_TOLEDO
            }, timeout=20)
            
            # Si el script devuelve el HTML de error de Google
            if "DOCTYPE html" in res.text:
                st.error("❌ ERROR DE PERMISOS EN GOOGLE")
                st.warning("Debes entrar al Apps Script y en 'Gestionar implementaciones' poner 'Quién tiene acceso: Cualquier persona'.")
            elif res.text.startswith("http"):
                st.success("✅ ¡ARCHIVO LOCALIZADO!")
                st.link_button("📥 DESCARGAR CERTIFICADO", res.text.strip())
            else:
                st.error(f"Respuesta del servidor: {res.text}")
                
        except Exception as e:
            st.error(f"Fallo de conexión: {str(e)}")

st.divider()
st.caption("Prueba de enlace final - Sergio 2026")