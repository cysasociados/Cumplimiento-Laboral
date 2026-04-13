import streamlit as st
import requests

# --- DATOS PROPORCIONADOS POR SERGIO ---
URL_APPS_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"
ID_CARPETA_TOLEDO = "11UQVAgZhkaCjt7BUofsjPcf_HybC-Qi6"
NOMBRE_ARCHIVO = "Certificado.122025.pdf"

st.title("🧪 Test de Conexión Directa a Drive")
st.write(f"**Empresa:** TOLEDO GANZO")
st.write(f"**Archivo buscado:** `{NOMBRE_ARCHIVO}`")
st.write(f"**ID Carpeta:** `{ID_CARPETA_TOLEDO}`")

st.divider()

if st.button("🚀 Ejecutar Prueba de Descarga"):
    with st.spinner("Consultando con Google Drive..."):
        try:
            # Construimos la URL de consulta
            params = {
                "nombre": NOMBRE_ARCHIVO,
                "carpeta": ID_CARPETA_TOLEDO
            }
            
            # Realizamos la petición al Apps Script
            response = requests.get(URL_APPS_SCRIPT, params=params, timeout=15)
            
            st.write("---")
            st.write("**Resultado del Servidor:**")
            
            if response.text.startswith("http"):
                st.success("✅ ¡CONEXIÓN EXITOSA!")
                st.write("El archivo fue encontrado correctamente.")
                st.link_button("📥 Descargar Archivo", response.text.strip())
                st.code(response.text, language="text")
            else:
                st.error("❌ ARCHIVO NO ENCONTRADO")
                st.write(f"El servidor respondió: `{response.text}`")
                st.info("""
                **Posibles causas del fallo:**
                1. El archivo en Drive no se llama exactamente `Certificado.122025.pdf` (revisa mayúsculas/minúsculas).
                2. El archivo no está dentro de la carpeta con ID `11UQVAgZhkaCjt7BUofsjPcf_HybC-Qi6`.
                3. El Apps Script no tiene permisos para acceder a esa carpeta específica.
                """)
                
        except Exception as e:
            st.error(f"💥 Error crítico de conexión: {e}")

st.divider()
st.caption("Herramienta de diagnóstico rápido - Control Laboral 2026")