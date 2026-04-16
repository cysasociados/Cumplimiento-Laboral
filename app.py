import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# 1. CONFIGURACION INICIAL
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# CABECERA
col_logo_l, col_espacio, col_logo_r = st.columns([2, 4, 1])
with col_logo_l:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", width=250)
    else: st.subheader("Minera San Geronimo")
with col_logo_r:
    if os.path.exists("cys.png"): st.image("cys.png", width=120)
    else: st.write("C&S Asociados")

# CONEXION
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxuGe9TQYwyKDHPaKJKiR8XqD14Uk7s8vk9BksMCGNBJb-0BZFj8ztWek9pJ3nDkXIBtQ/exec"
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# MAPEOS
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARP = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, p):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={p}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# LOGIN
if "authenticated" not in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("Acceso CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                em_v = u.get('EMAIL')
                email_u = str(em_v).strip() if pd.notna(em_v) else 'cumplimiento@cysasociados.cl'
                st.session_state.update({"authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA',''), "u_email": email_u})
                st.rerun()
            else: st.error("Clave invalida")
    st.stop()

# SIDEBAR
with st.sidebar:
    st.header("Configuracion")
    anio_global = st.selectbox("Anio", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MAPA_MESES_NUM.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Analisis", ["AÑO COMPLETO"] + cols_m)
    st.write(f"Usuario: {st.session_state['u_nom']}")
    if st.button("Cerrar Sesion"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# TABS
rol = st.session_state["u_rol"]
if rol == "USUARIO": t_list = ["Mi Avance", "Dotacion", "Carga Doc"]
else: t_list = ["Avance Global", "Empresas", "Dotacion", "Carga Doc", "Admin"]
tabs = st.tabs(t_list)

# TAB 1: DASHBOARD
with tabs[0]:
    df_id_f = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        c_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        df_num = df_f[c_filt].apply(pd.to_numeric, errors='coerce')

        # EXCLUSION ESTADO 9
        df_audit = df_num.copy()
        df_audit[df_audit == 9] = pd.NA
        t_p = df_audit.count().sum()
        t_5 = (df_audit == 5).sum().sum()
        perc = (t_5 / t_p * 100) if t_p > 0 else 0

        # KPI AL DIA
        if mes_sidebar == "AÑO COMPLETO":
            al_dia = df_audit.apply(lambda x: x.dropna().eq(5).all() if x.dropna().size > 0 else False, axis=1).sum()
        else: al_dia = (df_audit == 5).sum().sum()

        st.header(f"Dashboard - {mes_sidebar} {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento Real", f"{perc:.1f}%")
        k3.metric("Empresas 100% Al Dia", int(al_dia))

        # CANTIDAD POR ESTADOS
        st.write("### Periodos por Estado")
        st_c = df_num.stack().value_counts()
        m_cols = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            m_cols[i].metric(name, int(st_c.get(code, 0)))

        # GRAFICO BARRAS
        if mes_sidebar == "AÑO COMPLETO":
            res_evo = []
            for m in cols_m:
                c_m = df_f[m].value_counts()
                for cod, cant in c_m.items():
                    if pd.notna(cod):
                        res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        
        c_pie, c_desc = st.columns([3, 1])
        with c_pie:
            p_d = df_es[cols_m].stack().value_counts().reset_index()
            p_d.columns = ['Cod', 'Cant']; p_d['Estado'] = p_d['Cod'].map(MAPA_ESTADOS)
            p_final = p_d[p_d['Cod'] != 9]
            st.plotly_chart(px.pie(p_final, values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS), use_container_width=True)
            
            # HISTORIAL 2 LINEAS
            st.write("#### Historial Mensual")
            m1, m2 = cols_m[:6], cols_m[6:]
            r1 = st.columns(6)
            for i, m in enumerate(m1):
                val = int(df_es[m].values[0]) if pd.notna(df_es[m].values[0]) else 8
                r1[i].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:5px; border-radius:5px;'><b>{m}</b><br><small>{MAPA_ESTADOS.get(val)}</small></div>", unsafe_allow_html=True)
            st.write("")
            r2 = st.columns(6)
            for i, m in enumerate(m2):
                val = int(df_es[m].values[0]) if pd.notna(df_es[m].values[0]) else 8
                r2[i].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:5px; border-radius:5px;'><b>{m}</b><br><small>{MAPA_ESTADOS.get(val)}</small></div>", unsafe_allow_html=True)

        with c_desc:
            st.write("#### Certificados")
            m_p = st.selectbox("Mes:", cols_m)
            if st.button("Buscar PDF"):
                match = df_id_f[df_id_f.iloc[:,1].str.contains(emp_sel[:10], case=False, na=False)]
                if not match.empty:
                    id_f = str(match.iloc[0][0]).strip()
                    n_f = f"Certificado.{MAPA_MESES_NUM[m_p]}{anio_global}.pdf"
                    with st.spinner("Buscando..."):
                        r = requests.get(URL_APPS_SCRIPT, params={"nombre": n_f, "carpeta": id_f})
                        if r.text.startswith("http"): st.link_button("Descargar", r.text.strip())
                        else: st.error("No encontrado")

# DOTACION
with tabs[2]:
    st.header(f"Dotacion - {anio_global}")
    mes_masa = st.selectbox("Mes Masa:", list(MAPA_MESES_NUM.keys()), key="m_masa")
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_masa.capitalize()}{anio_global[-2:]}")
    if not df_m.empty:
        c_rs = next((c for c in df_m.columns if 'RAZON' in str(c).upper()), df_m.columns[0])
        df_mf = df_m[df_m[c_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m
        st.dataframe(df_mf, use_container_width=True)

# CARGA
with tabs[3]:
    st.header("Carga de Documentos")
    if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione mes")
    else:
        emp_u = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa:", sorted(df_av[col_e].unique()))
        docs = [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]
        for n, p in docs:
            c1, c2 = st.columns([3, 1])
            arch = c1.file_uploader(f"Subir {n}", type=["pdf"], key=f"u_{p}")
            if c2.button(f"Cargar {p}", key=f"b_{p}"):
                if arch:
                    m_u = cargar_datos(ID_EMPRESAS, "HOJA1")
                    mt = m_u[m_u.iloc[:,1].str.contains(emp_u[:10], case=False, na=False)]
                    if not mt.empty:
                        id_f_u = str(mt.iloc[0][0]).strip()
                        payload = {"nombre_final": f"{p}_{mes_sidebar}_{anio_global}_{emp_u[:10]}.pdf", "id_carpeta": id_f_u, "anio": anio_global, "mes_nombre": MAPA_MESES_CARP[mes_sidebar], "mimetype": "application/pdf", "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')}
                        r = requests.post(URL_APPS_SCRIPT, data=payload)
                        if "✅" in r.text or "Exito" in r.text: st.success("Cargado"); st.balloons()
        st.divider()
        if st.button("Finalizar Proceso", use_container_width=True):
            p_e = {"accion": "enviar_email", "empresa": emp_u, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
            r = requests.post(URL_APPS_SCRIPT, data=p_e)
            if "✅" in r.text: st.success("Notificado"); st.balloons()

st.caption("CMSG | C&S Asociados Ltda.")