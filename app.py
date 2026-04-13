import streamlit as st
import requests

# --- CONFIGURACIÓN ---
# ⚠️ PEGA AQUÍ LA NUEVA URL QUE COPIASTE EN EL PASO 2
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxbH7GCm95Eh0DMkBCNVD9Ce-lywoCqmUC_DraHw7DopQPeIOJ5XamcqHvf0dyBFtw/exec"

ID_CARPETA_TOLEDO = "11UQVAgZhkaCjt7BUofsjPcf_HybC-Qi6"
NOMBRE_ARCHIVO = "Certificado.122025.pdf"

st.set_page_config(page_title="Portal Auditoría", page_icon="🛡️")
st.title("🛡️ Portal de Auditoría Laboral")
st.subheader("Control de Documentos Drive")

st.info(f"📁 Buscando: `{NOMBRE_ARCHIVO}`")

if st.button("🚀 Consultar Documento"):
    with st.spinner("Conectando con Google Cloud..."):
        try:
            # Enviamos la consulta limpia
            res = requests.get(URL_APPS_SCRIPT, params={
                "nombre": NOMBRE_ARCHIVO,
                "carpeta": ID_CARPETA_TOLEDO
            }, timeout=20)
            
            respuesta_servidor = res.text.strip()
            
            if respuesta_servidor.startswith("http"):
                st.success("✅ ¡ARCHIVO LOCALIZADO!")
                st.balloons()
                st.link_button("📥 ABRIR / DESCARGAR CERTIFICADO", respuesta_servidor)
            else:
                st.error("❌ NO SE PUDO OBTENER EL ARCHIVO")
                st.warning(f"Respuesta de Google: {respuesta_servidor}")
                st.info("💡 RECOMENDACIÓN: Verifica que la CARPETA en Drive tenga el acceso compartido como 'Cualquier persona con el enlace puede leer'.")
                
        except Exception as e:
            st.error(f"Hubo un fallo en la conexión: {str(e)}")

st.divider()
st.caption("Conexión segura vía C&S Asociados Ltda.")