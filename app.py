¡Excelente, Sergio! Vamos por ese ajuste fino. Tienes mucha razón: un sistema de auditoría debe ser flexible pero riguroso. Si una empresa tiene estados 9 ("No Corresponde"), estos deben ser invisibles para la estadística, permitiendo que la empresa alcance su 100% de cumplimiento sobre lo que sí le corresponde informar.

He corregido la lógica del KPI "Al Día" y transformado el historial en una lista paralela (usando columnas) para que sea más visual y menos "cuadriculada" que una tabla.

🐍 app.py: Versión Refinada (Cálculo 100% Real + Lista Paralela)
Copia este código completo. He verificado que ahora la lógica para "Empresas al Día" considere el estado 9 como un "pase" automático.

Python
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE PANTALLA Y RELOJ CHILENO
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# --- CABECERA INSTITUCIONAL (LOGOS) ---
col_logo_l, col_espacio, col_logo_r = st.columns([2, 4, 1])
with col_logo_l:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", width=250)
    else: st.subheader("🏢 Minera San Gerónimo")
with col_logo_r:
    if os.path.exists("cys.png"): st.image("cys.png", width=120)
    else: st.write("**C&S Asociados**")

# --- CONFIGURACIÓN DE CONEXIÓN ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbz0twB53lP3FXsKcYFeuiveudxWjHnJ8MBomDV1sGRl2SUqnPVeYay3BHKXhTg-hTe1hg/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# MAPEOS Y CONFIGURACIONES
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARPETAS = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- 2. SISTEMA DE LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                ahora_chile = datetime.now(chile_tz)
                email_val = u.get('EMAIL')
                email_user = str(email_val).strip() if pd.notna(email_val) else 'cumplimiento@cysasociados.cl'
                st.session_state.update({"authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA',''), "u_email": email_user})
                st.session_state["log_accesos"].append({"Fecha": ahora_chile.strftime("%d/%m/%Y"), "Hora": ahora_chile.strftime("%H:%M:%S"), "Usuario": u.get('NOMBRE',''), "Empresa": u.get('EMPRESA','')})
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    anio_global = st.selectbox("Año de Análisis", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MAPA_MESES_NUM.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    if st.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- 4. TABS ---
rol = st.session_state["u_rol"]
if rol == "ADMIN": tab_list = ["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga de Documentos", "⚙️ Admin"]
elif rol == "REVISOR": tab_list = ["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga de Documentos"]
else: tab_list = ["📈 Mi Avance", "👥 Masa Laboral", "📤 Carga de Documentos"]
tabs = st.tabs(tab_list)

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    df_id_folders = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        df_num = df_f[cols_filt].apply(pd.to_numeric, errors='coerce')

        # --- LÓGICA DE AUDITORÍA: EXCLUSIÓN DEL ESTADO 9 ---
        # df_audit tiene NaNs donde había un 9.
        df_audit = df_num[df_num.isin([1, 2, 3, 4, 5, 8])] 
        total_periodos = df_audit.count().sum()
        total_cumple = (df_audit == 5).sum().sum()
        cumplimiento_perc = (total_cumple / total_periodos * 100) if total_periodos > 0 else 0

        # --- LÓGICA "AL DÍA" REFINADA ---
        # Una empresa está "Al Día" si en todos los meses que NO son '9', el estado es '5'.
        if mes_sidebar == "AÑO COMPLETO":
            # Filtramos los meses auditables para cada fila y verificamos si todos son igual a 5
            al_dia_count = df_audit.apply(lambda x: x.dropna().eq(5).all() if x.dropna().size > 0 else False, axis=1).sum()
        else:
            al_dia_count = (df_audit == 5).sum().sum()

        st.header(f"Dashboard de Gestión - {mes_sidebar} {anio_global}")
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas en Panel", len(df_f))
        k2.metric("% Cumplimiento Real", f"{cumplimiento_perc:.1f}%", help="Ignora periodos 'No Corresp.'")
        k3.metric("Empresas 100% Al Día", int(al_dia_count), help="Empresas que cumplen en todos sus meses auditables.")

        st.write("### 📊 Cantidad de Periodos por Estado")
        st_counts = df_num.stack().value_counts()
        m_cols = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            m_cols[i].metric(name, int(st_counts.get(code, 0)))

        st.divider()
        st.subheader("🎯 Análisis Detallado por Empresa")
        emp_sel = st.selectbox("Seleccione Empresa para visualizar:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        
        col_analisis, col_cert = st.columns([3, 1])
        with col_analisis:
            # Gráfico Circular Auditado (Sin el 9)
            pie_data = df_es[cols_m].stack().value_counts().reset_index()
            pie_data.columns = ['Cod', 'Cant']; pie_data['Estado'] = pie_data['Cod'].map(MAPA_ESTADOS)
            pie_audit = pie_data[pie_data['Cod'] != 9]
            st.plotly_chart(px.pie(pie_audit, values='Cant', names='Estado', hole=.4, 
                                  color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Estatus Anual: {emp_sel}"), use_container_width=True)
            
            # --- LISTA PARALELA (BAJO EL GRÁFICO) ---
            st.write("#### 📜 Historial Mensual")
            hist = df_es[cols_m].T.reset_index()
            hist.columns = ['Mes', 'Cod']; hist['Estado'] = hist['Cod'].map(MAPA_ESTADOS)
            
            # Formato de lista paralela usando columnas
            l_cols = st.columns(4) 
            for idx, h_row in hist.iterrows():
                l_cols[idx % 4].write(f"**{h_row['Mes']}**: {h_row['Estado']}")

        with col_cert:
            st.write("#### 📥 Certificados")
            m_pdf = st.selectbox("Seleccione Mes:", cols_m)
            if st.button("🔍 Buscar Certificado PDF"):
                match = df_id_folders[df_id_folders.iloc[:, 1].str.contains(emp_sel[:10], case=False, na=False)]
                if not match.empty:
                    id_folder = str(match.iloc[0][0]).strip()
                    nombre_f = f"Certificado.{MAPA_MESES_NUM[m_pdf]}{anio_global}.pdf"
                    with st.spinner("Buscando..."):
                        r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_folder})
                        if r.text.startswith("http"):
                            st.success("✅ Encontrado")
                            st.link_button("📥 DESCARGAR", r.text.strip())
                        else: st.error("No disponible.")

# --- TAB 2: MASA LABORAL ---
with tabs[1]:
    st.header(f"Dotación de Personal - {anio_global}")
    mes_m = st.selectbox("Filtrar Mes:", list(MAPA_MESES_NUM.keys()), key="m_masa")
    df_masa = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio_global[-2:]}")
    if not df_masa.empty:
        col_rs = next((c for c in df_masa.columns if 'RAZON' in str(c).upper()), df_masa.columns[0])
        df_mf = df_masa[df_masa[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_masa
        col_cont = next((c for c in df_mf.columns if 'CONTRATO' in str(c).upper()), None)
        if col_cont:
            pf = df_mf[df_mf[col_cont].str.contains("PLAZO FIJO", case=False, na=False)]
            if not pf.empty:
                st.warning(f"Se detectaron {len(pf)} trabajadores con contrato a Plazo Fijo.")
                st.dataframe(pf, use_container_width=True)
            else: st.success("✅ Todo el personal analizado tiene contrato Indefinido.")
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Dotación Total", len(df_mf))
        if 'NACIONALIDAD' in df_mf.columns:
            ext = len(df_mf[~df_mf['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Extranjeros", ext)
        if 'TOTALHORASEXTRA' in df_mf.columns:
            m3.metric("HH.EE Mes", f"{pd.to_numeric(df_mf['TOTALHORASEXTRA'], errors='coerce').sum():,.0f}")
        st.dataframe(df_mf, use_container_width=True)

# --- TAB 3: CARGA DE DOCUMENTOS ---
with tabs[2]:
    st.header("📤 Pasarela de Carga")
    if mes_sidebar == "AÑO COMPLETO": st.warning("⚠️ Seleccione un mes específico en el panel lateral.")
    else:
        emp_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa Destino:", sorted(df_av[col_e].unique()))
        docs = [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]
        for n, p in docs:
            c1, c2 = st.columns([3, 1])
            arch = c1.file_uploader(f"Subir {n}", type=["pdf"], key=f"up_{p}")
            if c2.button(f"🚀 Cargar {p}", key=f"btn_{p}"):
                if arch:
                    df_ids_up = cargar_datos(ID_EMPRESAS, "HOJA1")
                    match_u = df_ids_up[df_ids_up.iloc[:,1].str.contains(emp_up[:10], case=False, na=False)]
                    if not match_u.empty:
                        id_f_up = str(match_u.iloc[0][0]).strip()
                        payload = {"nombre_final": f"{p}_{mes_sidebar}_{anio_global}_{emp_up[:10]}.pdf", "id_carpeta": id_f_up, "anio": anio_global, "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar], "mimetype": "application/pdf", "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')}
                        with st.spinner("Subiendo..."):
                            r = requests.post(URL_APPS_SCRIPT, data=payload)
                            if "✅" in r.text or "Exito" in r.text: st.success("¡Cargado!"); st.balloons()
                else: st.warning("Seleccione archivo.")
        st.divider()
        if st.button("✅ ENVIAR NOTIFICACIÓN DE CARGA FINALIZADA", use_container_width=True):
            p_e = {"accion": "enviar_email", "empresa": emp_up, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
            with st.spinner("Enviando aviso..."):
                r = requests.post(URL_APPS_SCRIPT, data=p_e)
                if "✅" in r.text: st.success("¡Notificación enviada!"); st.balloons()

# --- TAB ADMIN ---
if rol == "ADMIN":
    with tabs[-1]:
        st.header("⚙️ Admin")
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("CMSG | C&S Asociados Ltda.")