import streamlit as st
import pandas as pd
import requests, base64, re, os, pytz
from datetime import datetime

# 1. CONFIGURACIÓN Y RELOJ CHILE
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# --- CABECERA ---
st.title("🛡️ Portal de Gestión CMSG")
st.markdown("---")

# --- CONEXIÓN DRIVE (Tu URL 100% Autorizada) ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbz0twB53lP3FXsKcYFeuiveudxWjHnJ8MBomDV1sGRl2SUqnPVeYay3BHKXhTg-hTe1hg/exec"

# IDs DE TUS PLANILLAS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

M_MES = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

@st.cache_data(ttl=10)
def cargar_datos(sid, p):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={p}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- 2. SISTEMA DE LOGIN ---
if "authenticated" not in st.session_state:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔐 Acceso Clientes")
        pwd = st.text_input("Ingrese su Clave:", type="password").strip()
        if st.button("Entrar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            # Buscamos la clave en la columna CLAVE (columna 3)
            match = df_u[df_u.iloc[:, 2].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                st.session_state.update({
                    "authenticated": True, 
                    "u_nom": u.get('NOMBRE','Usuario'), 
                    "u_emp": u.get('EMPRESA','CMSG'), 
                    "u_email": u.get('EMAIL','cumplimiento@cysasociados.cl')
                })
                st.rerun()
            else: st.error("❌ Clave incorrecta")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.write(f"👤 **{st.session_state['u_nom']}**")
    st.caption(f"🏢 {st.session_state['u_emp']}")
    anio = st.selectbox("Año", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio)
    mes = st.selectbox("Mes", [c for c in df_av.columns if c in M_MES.keys()])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- 4. TABS ---
tabs = st.tabs(["📊 Mi Avance", "📤 Carga de Documentos"])

with tabs[0]:
    st.header(f"Estado de Cumplimiento - {mes} {anio}")
    df_f = df_av[df_av.iloc[:,0] == st.session_state["u_emp"]]
    st.dataframe(df_f, use_container_width=True)

with tabs[1]:
    st.header("📤 Pasarela de Archivos PDF")
    empresa = st.session_state['u_emp']
    
    docs_config = [("Liquidaciones de Sueldo", "LIQ"), ("Planilla Previred", "PREVIRED"), ("Certificado F30", "F30"), ("Certificado F30-1", "F30_1")]
    
    for nombre, pref in docs_config:
        c1, c2 = st.columns([3, 1])
        archivo = c1.file_uploader(f"Seleccionar {nombre}", type=["pdf"], key=f"file_{pref}")
        if c2.button(f"Subir {pref}", key=f"btn_{pref}"):
            if archivo:
                df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
                try:
                    # Buscamos el ID de la carpeta (primera columna del Excel de empresas)
                    id_f = str(df_id[df_id.iloc[:,1].str.contains(empresa[:10], na=False, case=False)].iloc[0][0])
                    payload = {
                        "nombre_final": f"{pref}_{mes}_{anio}_{empresa[:10]}.pdf",
                        "id_carpeta": id_f, "anio": anio, "mes_nombre": M_MES[mes],
                        "mimetype": "application/pdf", 
                        "archivo_base64": base64.b64encode(archivo.read()).decode('utf-8')
                    }
                    with st.spinner(f"Cargando {pref}..."):
                        r = requests.post(URL_APPS_SCRIPT, data=payload)
                        if "✅" in r.text or "Exito" in r.text: 
                            st.success(f"✅ {pref} subido correctamente.")
                except:
                    st.error("❌ No se encontró la carpeta de destino.")
            else:
                st.warning("⚠️ Seleccione un archivo.")

    st.markdown("---")
    st.subheader("🏁 Notificación de Término")
    st.info("Al presionar este botón, se enviará un comprobante de carga a C&S Asociados y una copia para ti.")
    if st.button("🏁 FINALIZAR CARGA Y NOTIFICAR POR EMAIL", use_container_width=True):
        payload_email = {
            "accion": "enviar_email",
            "empresa": empresa,
            "usuario": st.session_state["u_nom"],
            "periodo": f"{mes} {anio}",
            "email_usuario": st.session_state["u_email"]
        }
        with st.spinner("Enviando comprobante oficial..."):
            try:
                r = requests.post(URL_APPS_SCRIPT, data=payload_email)
                if "✅" in r.text or "correctamente" in r.text:
                    st.balloons()
                    st.success("¡Excelente! Notificación enviada. Revisa tu correo.")
                else:
                    st.error(f"Detalle de Google: {r.text}")
            except:
                st.error("No se pudo conectar con el motor de correos.")

st.caption("CMSG | C&S Asociados Ltda. - Control Laboral v3.0")