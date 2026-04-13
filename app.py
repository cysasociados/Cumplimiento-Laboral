import streamlit as st
import requests

# --- CONFIGURACIÓN ---
# Asegúrate de que esta URL sea la de la NUEVA implementación
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFTw/exec"

ID_CARPETA_TOLEDO = "11UQVAgZhkaCjt7BUofsjPcf_HybC-Qi6"
NOMBRE_ARCHIVO = "Certificado.122025.pdf"

st.set_page_config(page_title="Portal Auditoría", page_icon="🛡️")
st.title("🛡️ Portal de Auditoría Laboral")

st.info(f"📁 Buscando: `{NOMBRE_ARCHIVO}`")

if st.button("🚀 Consultar Documento"):
    with st.spinner("Conectando con Google Cloud..."):
        try:
            res = requests.get(URL_APPS_SCRIPT, params={
                "nombre": NOMBRE_ARCHIVO,
                "carpeta": ID_CARPETA_TOLEDO
            }, timeout=20)
            
            # Detectamos si Google nos está mandando a la página de login
            if "accounts.google.com" in res.text or "signin" in res.text:
                st.error("🔒 ERROR DE PERMISOS: Google pide iniciar sesión.")
                st.warning("⚠️ ACCIÓN REQUERIDA: En el Apps Script, ve a 'Gestionar implementaciones' y cambia 'Quién tiene acceso' a 'Cualquier persona'. Luego guarda y vuelve a probar.")
            elif res.text.startswith("http"):
                st.success("✅ ¡ARCHIVO LOCALIZADO!")
                st.balloons()
                st.link_button("📥 DESCARGAR CERTIFICADO", res.text.strip())
            else:
                st.error(f"Respuesta del servidor: {res.text}")
                
        except Exception as e:
            st.error(f"Fallo de conexión: {str(e)}")

st.divider()
st.caption("Validación de seguridad - Sergio 2026")