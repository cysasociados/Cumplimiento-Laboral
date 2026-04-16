import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# --- CABECERA ---
col_logo_l, col_espacio, col_logo_r = st.columns([2, 4, 1])
with col_logo_l:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", width=250)
    else: st.subheader("🏢 Minera San Gerónimo")
with col_logo_r:
    if os.path.exists("cys.png"): st.image("cys.png", width=120)
    else: st.write("**C&S Asociados**")

# --- CONEXIÓN ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbzo_2sWz7VKFxQZ9iVvcCadEGmBIPsQzMkJCDw8zzRPPFLJybi7_jUw2v0ebdulvzuQYg/exec"
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARPETAS = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, p):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={p}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🔐 Acceso CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                ahora_ch = datetime.now(chile_tz)
                email_v = u.get('EMAIL')
                email_u = str(email_v).strip() if pd.notna(email_v) else 'cumplimiento@cysasociados.cl'
                st.session_state.update({"authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA',''), "u_email": email_u})
                st.session_state["log_accesos"].append({"Fecha": ahora_ch.strftime("%d/%m/%Y"), "Hora": ahora_ch.strftime("%H:%M:%S"), "Usuario": u.get('NOMBRE',''), "Empresa": u.get('EMPRESA','')})
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    anio_global = st.selectbox("Año", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MAPA_MESES_NUM.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    if st.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- TABS ---
rol = st.session_state["u_rol"]
if rol == "USUARIO": tab_list = ["📈 Mi Avance", "👥 Masa Laboral", "📤 Carga de Documentos"]
else: tab_list = ["📈 Avance Global", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga de Documentos", "⚙️ Admin"]
tabs = st.tabs(tab_list)

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    df_id_folders = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        df_num = df_f[cols_filt].apply(pd.to_numeric, errors='coerce')

        # --- MATEMÁTICA REAL (ESTADO 9 FUERA) ---
        df_audit = df_num.copy()
        df_audit[df_audit == 9] = pd.NA
        total_p = df_audit.count().sum()
        total_5 = (df_audit == 5).sum().sum()
        perc_real = (total_5 / total_p * 100) if total_p > 0 else 0

        # --- KPI EMPRESAS AL DÍA ---
        if mes_sidebar == "AÑO COMPLETO":
            # Si todos los meses auditables (no NaNs) son 5, está al día.
            al_dia_count = df_audit.apply(lambda x: x.dropna().eq(5).all() if x.dropna().size > 0 else False, axis=1).sum()
        else:
            al_dia_count = (df_audit == 5).sum().sum()

        st.header(f"Dashboard de Auditoría - {mes_sidebar} {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento Real", f"{perc_real:.1f}%", help="Ignora estados 9")
        k3.metric("Empresas 100% Al Día", int(al_dia_count))

        st.divider()
        st.subheader("🎯 Detalle por Empresa y Certificados")
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        
        col_pie, col_desc = st.columns([3, 1])
        with col_pie:
            # Gráfico Circular
            pie_data = df_es[cols_m].stack().value_counts().reset_index()
            pie_data.columns = ['Cod', 'Cant']; pie_data['Estado'] = pie_data['Cod'].map(MAPA_ESTADOS)
            pie_final = pie_data[pie_data['Cod'] != 9]
            st.plotly_chart(px.pie(pie_final, values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Distribución: {emp_sel}"), use_container_width=True)
            
            # --- HISTORIAL EN DOS LÍNEAS (TABLA HORIZONTAL 6x2) ---
            st.write("#### 📜 Historial Mensual")
            meses_1 = cols_m[:6]
            meses_2 = cols_m[6:]
            
            # Primera línea
            row1 = st.columns(6)
            for i, m in enumerate(meses_1):
                val = int(df_es[m].values[0]) if pd.notna(df_es[m].values[0]) else 8
                row1[i].markdown(f"<p style='text-align: center; margin-bottom: 0;'><b>{m}</b></p>", unsafe_allow_html=True)
                row1[i].markdown(f"<p style='text-align: center; font-size: 0.8em; color: gray;'>{MAPA_ESTADOS.get(val)}</p>", unsafe_allow_html=True)
            
            # Segunda línea
            row2 = st.columns(6)
            for i, m in enumerate(meses_2):
                val = int(df_es[m].values[0]) if pd.notna(df_es[m].values[0]) else 8
                row2[i].markdown(f"<p style='text-align: center; margin-bottom: 0;'><b>{m}</b></p>", unsafe_allow_html=True)
                row2[i].markdown(f"<p style='text-align: center; font-size: 0.8em; color: gray;'>{MAPA_ESTADOS.get(val)}</p>", unsafe_allow_html=True)

        with col_desc:
            st.write("#### 📥 Certificados")
            m_pdf = st.selectbox("Mes Certificado:", cols_m)
            if st.button("🔍 Obtener PDF"):
                # Recuperar el ID de la carpeta
                match = df_id_folders[df_id_folders.iloc[:,1].str.contains(emp_sel[:10], case=False, na=False)]
                if not match.empty:
                    id_folder = str(match.iloc[0][0]).strip()
                    nombre_pdf = f"Certificado.{MAPA_MESES_NUM[m_pdf]}{anio_global}.pdf"
                    with st.spinner("Buscando en Drive..."):
                        try:
                            # Llama a la función doGet del Apps Script
                            r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_pdf, "carpeta": id_folder})
                            if r.text.startswith("http"):
                                st.success("✅ Certificado encontrado")
                                st.link_button("📥 DESCARGAR AHORA", r.text.strip())
                            else: st.error("No disponible en Drive.")
                        except: st.error("Error de conexión.")

# --- TAB: MASA LABORAL ---
idx_masa = tab_list.index("👥 Masa Laboral") if "👥 Masa Laboral" in tab_list else tab_list.index("👥 Masa Colaboradores")
with tabs[idx_masa]:
    st.header(f"Nómina de Personal - {anio_global}")
    mes_m = st.selectbox("Mes Masa:", list(MAPA_MESES_NUM.keys()), key="m_masa")
    df_masa = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio_global[-2:]}")
    if not df_masa.empty:
        col_rs = next((c for c in df_masa.columns if 'RAZON' in str(c).upper()), df_masa.columns[0])
        df_mf = df_masa[df_masa[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_masa
        col_cont = next((c for c in df_mf.columns if 'CONTRATO' in str(c).upper()), None)
        if col_cont:
            pf = df_mf[df_mf[col_cont].str.contains("PLAZO FIJO", case=False, na=False)]
            if not pf.empty: st.warning(f"🚨 Alertas: {len(pf)} contratos a Plazo Fijo.")
        st.dataframe(df_mf, use_container_width=True)

# --- TAB: CARGA DE DOCUMENTOS ---
idx_carga = tab_list.index("📤 Carga de Documentos")
with tabs[idx_carga]:
    st.header("📤 Pasarela de Carga")
    if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione un mes específico.")
    else:
        emp_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa Destino:", sorted(df_av[col_e].unique()))
        docs = [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]
        for n, p in docs:
            c1, c2 = st.columns([3, 1])
            arch = c1.file_uploader(f"Subir {n}", type=["pdf"], key=f"up_{p}")
            if c2.button(f"🚀 Cargar {p}", key=f"btn_{p}"):
                if arch:
                    match_u = df_id_folders[df_id_folders.iloc[:,1].str.contains(emp_up[:10], case=False, na=False)]
                    if not match_u.empty:
                        id_f_up = str(match_u.iloc[0][0]).strip()
                        payload = {"nombre_final": f"{p}_{mes_sidebar}_{anio_global}_{emp_up[:10]}.pdf", "id_carpeta": id_f_up, "anio": anio_global, "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar], "mimetype": "application/pdf", "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')}
                        with st.spinner("Subiendo..."):
                            r = requests.post(URL_APPS_SCRIPT, data=payload)
                            if "✅" in r.text or "Exito" in r.text: st.success("¡Cargado!"); st.balloons()
        st.divider()
        if st.button("✅ FINALIZAR Y NOTIFICAR", use_container_width=True):
            p_e = {"accion": "enviar_email", "empresa": emp_up, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
            r = requests.post(URL_APPS_SCRIPT, data=p_e)
            if "✅" in r.text: st.success("¡Notificado!"); st.balloons()

st.caption("CMSG | C&S Asociados Ltda.")