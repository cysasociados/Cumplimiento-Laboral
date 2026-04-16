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
st.set_page_config(page_title="Control de Cumplimiento Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# CONEXIONES (IDS DE GOOGLE SHEETS)
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxuGe9TQYwyKDHPaKJKiR8XqD14Uk7s8vk9BksMCGNBJb-0BZFj8ztWek9pJ3nDkXIBtQ/exec"
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# MAPEOS DE ESTADOS Y COLORES
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MESES_LISTA = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
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

# 2. SISTEMA DE LOGIN
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("CMSG.png"): st.image("CMSG.png", width=220)
        st.title("Acceso Control Laboral CMSG")
        pwd = st.text_input("Ingrese su contraseña:", type="password").strip()
        if st.button("Ingresar al Portal", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
                if not match.empty:
                    u = match.iloc[0]
                    st.success(f"Bienvenido(a), {u.get('NOMBRE','')}")
                    st.session_state.update({
                        "authenticated": True, "u_nom": u.get('NOMBRE',''), 
                        "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA',''), 
                        "u_email": u.get('EMAIL','')
                    })
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
    st.stop()

# 3. PANEL LATERAL (SIDEBAR)
with st.sidebar:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", use_container_width=True)
    st.markdown("---")
    st.markdown(f"👤 **Usuario:** {st.session_state['u_nom']}")
    st.markdown(f"🏢 **Empresa:** {st.session_state['u_emp']}")
    st.markdown(f"🔑 **Rol:** {st.session_state['u_rol']}")
    st.markdown("---")
    anio_global = st.selectbox("Seleccione Año", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MESES_LISTA] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    if st.button("Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- CABECERA LOGO INTERNA ---
if os.path.exists("CMSG.png"): st.image("CMSG.png", width=180)

# 4. DEFINICION DE PESTAÑAS (TABS)
rol = st.session_state["u_rol"]
tab_list = ["📉 Dashboard", "👥 Dotación", "📤 Carga Doc"] if rol == "USUARIO" else ["📉 Avance Global", "🏢 Empresas", "👥 Dotación", "📤 Carga Doc", "⚙️ Admin"]
tabs = st.tabs(tab_list)

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    df_id_empresas = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        c_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        df_num = df_f[c_filt].apply(pd.to_numeric, errors='coerce')

        # Matematica Real (Exclusión Estado 9)
        df_audit = df_num.copy(); df_audit[df_audit == 9] = pd.NA
        t_p = df_audit.count().sum(); t_5 = (df_audit == 5).sum().sum()
        perc = (t_5 / t_p * 100) if t_p > 0 else 0

        st.header(f"Gestión de Cumplimiento - {mes_sidebar} {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento Real", f"{perc:.1f}%")
        k3.metric("Al Día", int(df_audit.apply(lambda x: x.dropna().eq(5).all() if x.dropna().size > 0 else False, axis=1).sum() if mes_sidebar == "AÑO COMPLETO" else (df_audit == 5).sum().sum()))

        # Recuento de Estados
        st.write("###")
        st_c = df_num.stack().value_counts()
        m_cols_res = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            m_cols_res[i].metric(name, int(st_c.get(code, 0)))

        # 📈 GRAFICO BARRAS (JUSTO DEBAJO DE METRICAS)
        if mes_sidebar == "AÑO COMPLETO":
            st.divider()
            st.write("### Evolución Mensual de Estados")
            res_evo = []
            for m in cols_m:
                counts_m = df_f[m].value_counts()
                for cod, cant in counts_m.items():
                    if pd.notna(cod): res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo: st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()
        emp_sel = st.selectbox("Seleccione Empresa para Detalle:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        col_izq, col_der = st.columns([3, 1.2])

        with col_izq:
            # Gráfico Circular
            p_d = df_es[cols_m].stack().value_counts().reset_index()
            p_d.columns = ['Cod', 'Cant']; p_d['Estado'] = p_d['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(p_d[p_d['Cod'] != 9], values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Estatus: {emp_sel}"), use_container_width=True)
            
            # HISTORIAL CROMÁTICO (DEBAJO DEL GRAFICO)
            st.write("#### 📜 Historial Mensual")
            m1, m2 = cols_m[:6], cols_m[6:]
            def dibujar_grid(lista):
                cols = st.columns(6)
                for i, m in enumerate(lista):
                    v_val = df_es[m].values[0]
                    v = int(v_val) if pd.notna(v_val) else 8
                    t = MAPA_ESTADOS.get(v, "Sin Info"); b = COLORES_ESTADOS.get(t, "#555555")
                    c = "#000000" if t in ["Observado", "Cumple", "En Revision"] else "#FFFFFF"
                    cols[i].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:8px; border-radius:8px; background-color:{b}; color:{c}; min-height:65px; display:flex; flex-direction:column; justify-content:center;'><b style='font-size:13px;'>{m}</b><br><span style='font-size:9px; font-weight:bold;'>{t.upper()}</span></div>", unsafe_allow_html=True)
            dibujar_grid(m1); st.write(""); dibujar_grid(m2)

        with col_der:
            # DESCARGA INTEGRADA
            st.subheader("📄 Certificado")
            m_pdf_sel = st.selectbox("Mes para PDF:", cols_m, key="sel_pdf")
            if "last_selection" not in st.session_state or st.session_state["last_selection"] != f"{emp_sel}_{m_pdf_sel}":
                st.session_state["last_selection"] = f"{emp_sel}_{m_pdf_sel}"
                if "link_descarga" in st.session_state: del st.session_state["link_descarga"]
            
            if st.button("🔍 Obtener PDF", use_container_width=True):
                match_id = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_sel[:10], case=False, na=False)]
                if not match_id.empty:
                    id_f = str(match_id.iloc[0]['IDCARPETA']).strip()
                    n_f = f"Certificado.{MAPA_MESES_NUM[m_pdf_sel]}{anio_global}.pdf"
                    r = requests.get(URL_APPS_SCRIPT, params={"nombre": n_f, "carpeta": id_f}, timeout=15)
                    if r.text.startswith("http"): st.session_state["link_descarga"] = r.text.strip()
                    else: st.error("No se encontró el archivo.")
            if "link_descarga" in st.session_state: st.link_button("📥 DESCARGAR PDF", st.session_state["link_descarga"], use_container_width=True)
            
            st.divider(); st.subheader("📝 Observaciones")
            col_o = next((c for c in df_av.columns if 'OBS' in str(c).upper()), None)
            if col_o and pd.notna(df_es.iloc[0][col_o]): st.warning(df_es.iloc[0][col_o])
            else: st.info("Sin observaciones.")

# --- TAB 2: DOTACIÓN ---
with tabs[tab_list.index("👥 Dotación")]:
    st.header(f"Dotación de Personal - {anio_global}")
    mes_dot = st.selectbox("Filtrar Mes:", MESES_LISTA, key="m_masa")
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_dot.capitalize()}{anio_global[-2:]}")
    if not df_m.empty:
        c_rs = next((c for c in df_m.columns if 'RAZON' in str(c).upper()), df_m.columns[0])
        st.dataframe(df_m[df_m[c_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m, use_container_width=True)

# --- TAB 4: CARGA DE DOCUMENTOS (EXCEL INCLUIDO) ---
with tabs[tab_list.index("📤 Carga Doc")]:
    st.header("📤 Pasarela de Carga")
    if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione un Mes específico en el panel lateral.")
    else:
        emp_u = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa Destino:", sorted(df_av[col_e].unique()), key="up_emp")
        st.info(f"Subiendo para: **{emp_u}** | Periodo: **{mes_sidebar} {anio_global}**")
        st.divider()
        docs_config = [
            ("📄 Liquidaciones de Sueldo", "LIQ", ["pdf"]),
            ("💰 Planilla Previred", "PREVIRED", ["pdf"]),
            ("📋 Certificado F30", "F30", ["pdf"]),
            ("🔍 Certificado F30-1", "F30_1", ["pdf"]),
            ("💸 Comprobante de Pagos", "PAGOS", ["pdf"]),
            ("📊 Planilla Control Mensual", "CONTROL", ["xlsx", "xls"])
        ]
        for nombre_doc, prefijo, extensiones in docs_config:
            c1, c2 = st.columns([3, 1])
            arch = c1.file_uploader(f"Subir {nombre_doc}", type=extensiones, key=f"u_{prefijo}")
            if c2.button(f"🚀 Cargar", key=f"b_{prefijo}", use_container_width=True):
                if arch:
                    mt = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_u[:10], case=False, na=False)]
                    if not mt.empty:
                        id_f_u = str(mt.iloc[0]['IDCARPETA']).strip()
                        ext = arch.name.split('.')[-1]
                        n_final = f"{prefijo}_{mes_sidebar}_{anio_global}_{emp_u[:10]}.{ext}"
                        mtype = "application/pdf" if ext == "pdf" else "application/vnd.ms-excel"
                        payload = {"nombre_final": n_final, "id_carpeta": id_f_u, "anio": anio_global, 
                                   "mes_nombre": MAPA_MESES_CARP[mes_sidebar], "mimetype": mtype, 
                                   "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')}
                        r = requests.post(URL_APPS_SCRIPT, data=payload)
                        if "Exito" in r.text: st.success("Documento cargado exitosamente.")
                else: st.warning("Seleccione un archivo.")
        st.divider()
        if st.button("🏁 FINALIZAR Y NOTIFICAR", use_container_width=True):
            p_e = {"accion": "enviar_email", "empresa": emp_u, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
            requests.post(URL_APPS_SCRIPT, data=p_e)
            st.success("Notificación enviada con éxito.")

# --- TAB 5: ADMIN (LOGS Y USUARIOS) ---
if rol != "USUARIO":
    with tabs[tab_list.index("⚙️ Admin")]:
        st.header("⚙️ Panel de Administración")
        st.subheader("Listado de Usuarios")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Sistema de Control Laboral CMSG | C & S Asociados Ltda.")