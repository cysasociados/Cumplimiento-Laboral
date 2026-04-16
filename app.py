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

# --- CABECERA INSTITUCIONAL ---
col_logo_l, col_espacio, col_logo_r = st.columns([2, 4, 1])
with col_logo_l:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", width=250)
    else: st.subheader("🏢 Minera San Gerónimo")
with col_logo_r:
    if os.path.exists("cys.png"): st.image("cys.png", width=120)
    else: st.write("**C&S Asociados**")

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Se mantiene la URL con permisos de email habilitados
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbz0twB53lP3FXsKcYFeuiveudxWjHnJ8MBomDV1sGRl2SUqnPVeYay3BHKXhTg-hTe1hg/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# MAPEOS Y CONFIGURACIONES
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MAPA_MESES_CARPETAS = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}

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

# --- 2. LOGIN (FUSIÓN V6 + V8) ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                ahora_chile = datetime.now(chile_tz)
                # Capturamos el email para notificaciones (v8)
                email_user = u.get('EMAIL', 'cumplimiento@cysasociados.cl')
                st.session_state["log_accesos"].append({
                    "Fecha": ahora_chile.strftime("%d/%m/%Y"), "Hora": ahora_chile.strftime("%H:%M:%S"),
                    "Usuario": u.get('NOMBRE',''), "Empresa": u.get('EMPRESA',''), "Rol": u.get('ROL','')
                })
                st.session_state.update({
                    "authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), 
                    "u_emp": u.get('EMPRESA',''), "u_email": email_user
                })
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    anio_global = st.selectbox("Año de Análisis", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MAPA_MESES_CARPETAS.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    st.caption(f"Rol: {st.session_state['u_rol']} | {st.session_state['u_emp']}")
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- 4. TABS POR ROL ---
rol = st.session_state["u_rol"]
if rol == "ADMIN": tab_list = ["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga", "⚙️ Admin"]
elif rol == "REVISOR": tab_list = ["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "📤 Carga"]
else: tab_list = ["📈 Mi Avance", "👥 Masa Laboral", "📤 Carga de Documentos"]
tabs = st.tabs(tab_list)

# --- TAB 1: AVANCE + DESCARGA (V6 INTEGRADA) ---
with tabs[0]:
    df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        cols_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        df_num = df_f[cols_filt].apply(pd.to_numeric, errors='coerce')

        st.header(f"Gestión de Control Laboral - {mes_sidebar} {anio_global}")
        
        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        t_p = df_num.isin([1,2,3,4,5]).sum().sum()
        t_5 = (df_num == 5).sum().sum()
        k2.metric("% Cumplimiento", f"{(t_5/t_p*100 if t_p > 0 else 0):.1f}%")
        k3.metric("Al Día", ((df_num == 5).all(axis=1)).sum() if not df_num.empty else 0)

        # Gráfico evolutivo (v6)
        if rol != "USUARIO" and mes_sidebar == "AÑO COMPLETO":
            res_evo = []
            for m in cols_m:
                counts = df_f[m].value_counts()
                for cod, cant in counts.items():
                    if pd.notna(cod):
                        res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', 
                                       color_discrete_map=COLORES_ESTADOS, barmode='stack', title="Evolución Mensual"), use_container_width=True)

        st.divider()
        st.subheader("🎯 Detalle Empresa y Descarga de Certificados")
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_e].unique()))
        row_e = df_f[df_f[col_e] == emp_sel].iloc[0]
        
        c_det, c_graf = st.columns([3, 2])
        with c_det:
            st.info(f"Visualizando: **{emp_sel}**")
            m_pdf = st.selectbox("Mes para Certificado PDF:", cols_m)
            if st.button(f"🔍 Obtener Certificado {m_pdf}"):
                col_id_f = next((c for c in df_id.columns if 'ID' in str(c).upper() or 'CARPETA' in str(c).upper()), 'IDCARPETA')
                match_id = df_id[df_id.iloc[:,1].str.contains(emp_sel[:10], case=False, na=False)]
                if not match_id.empty:
                    id_folder = str(match_id.iloc[0][col_id_f]).strip()
                    nombre_f = f"Certificado.{MAPA_MESES_NUM[m_pdf]}{anio_global}.pdf"
                    with st.spinner("Buscando..."):
                        r = requests.get(URL_APPS_SCRIPT, params={"nombre": nombre_f, "carpeta": id_folder})
                        if r.text.startswith("http"):
                            st.success("✅ Encontrado")
                            st.link_button("📥 Descargar Archivo", r.text.strip())
                        else: st.error("No disponible en Drive.")
        with c_graf:
            pie_data = [{'Estado': MAPA_ESTADOS.get(int(row_e[m]), "S/I")} for m in cols_m if pd.notna(row_e[m])]
            st.plotly_chart(px.pie(pd.DataFrame(pie_data), names='Estado', hole=.4, color_discrete_map=COLORES_ESTADOS), use_container_width=True)

# --- TAB: MASA COLABORADORES (V6 INTEGRADA) ---
idx_masa = tab_list.index("👥 Masa Colaboradores") if "👥 Masa Colaboradores" in tab_list else tab_list.index("👥 Masa Laboral")
with tabs[idx_masa]:
    st.header(f"Análisis de Dotación - {anio_global}")
    mes_masa = st.selectbox("Mes Nómina:", list(MAPA_MESES_NUM.keys()), key="masa_mes")
    df_masa = cargar_datos(ID_COLABORADORES, f"{mes_masa.capitalize()}{anio_global[-2:]}")
    if not df_masa.empty:
        col_rs = next((c for c in df_masa.columns if 'RAZON' in str(c).upper()), df_masa.columns[0])
        df_mf = df_masa[df_masa[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_masa
        
        # Alertas de Estabilidad (v6)
        st.subheader("🚨 Alertas de Estabilidad")
        col_cont = next((c for c in df_mf.columns if 'CONTRATO' in str(c).upper()), None)
        if col_cont:
            pf = df_mf[df_mf[col_cont].str.contains("PLAZO FIJO", case=False, na=False)]
            if not pf.empty:
                st.warning(f"Se detectaron {len(pf)} contratos a Plazo Fijo.")
                st.dataframe(pf, use_container_width=True)
            else: st.success("✅ Todo el personal tiene contrato Indefinido.")
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Dotación Total", len(df_mf))
        if 'NACIONALIDAD' in df_mf.columns:
            ext = len(df_mf[~df_mf['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Extranjeros", ext)
        if 'TOTALHORASEXTRA' in df_mf.columns:
            m3.metric("HH.EE del Mes", f"{pd.to_numeric(df_mf['TOTALHORASEXTRA'], errors='coerce').sum():,.0f}")
        st.dataframe(df_mf, use_container_width=True)

# --- TAB: CARGA DE DOCUMENTOS (V8 INTEGRADA) ---
idx_carga = tab_list.index("📤 Carga") if "📤 Carga" in tab_list else tab_list.index("📤 Carga de Documentos")
with tabs[idx_carga]:
    st.header("📤 Pasarela de Carga de Documentos")
    if mes_sidebar == "AÑO COMPLETO": st.warning("⚠️ Seleccione un mes en el panel lateral para habilitar la carga.")
    else:
        df_ids = cargar_datos(ID_EMPRESAS, "HOJA1")
        emp_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa Destino:", sorted(df_av[col_e].unique()))
        
        docs = [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]
        for nombre, pref in docs:
            c_f, c_b = st.columns([3, 1])
            arch = c_f.file_uploader(f"Subir {nombre}", type=["pdf"], key=f"f_{pref}")
            if c_b.button(f"🚀 Cargar {pref}", key=f"b_{pref}"):
                if arch:
                    match_u = df_ids[df_ids.iloc[:,1].str.contains(emp_up[:10], case=False, na=False)]
                    if not match_u.empty:
                        col_id_u = next((c for c in df_ids.columns if 'ID' in str(c).upper() or 'CARPETA' in str(c).upper()), 'IDCARPETA')
                        id_f_up = str(match_u.iloc[0][col_id_u]).strip()
                        payload = {
                            "nombre_final": f"{pref}_{mes_sidebar}_{anio_global}_{emp_up[:10]}.pdf",
                            "id_carpeta": id_f_up, "anio": anio_global, "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar],
                            "mimetype": "application/pdf", "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')
                        }
                        with st.spinner("Subiendo..."):
                            try:
                                r = requests.post(URL_APPS_SCRIPT, data=payload)
                                if "✅" in r.text: st.success(f"{pref} OK!"); st.balloons()
                                else: st.error(r.text)
                            except: st.error("Fallo de conexión.")
                else: st.warning("Seleccione un archivo.")

        st.divider()
        st.subheader("🏁 Finalizar y Notificar")
        if st.button("✅ Enviar Notificación de Carga Finalizada", use_container_width=True):
            p_e = {"accion": "enviar_email", "empresa": emp_up, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
            with st.spinner("Enviando aviso..."):
                try:
                    res = requests.post(URL_APPS_SCRIPT, data=p_e, timeout=20)
                    if "✅" in res.text: st.success("¡Email enviado con éxito!"); st.balloons()
                    else: st.error(f"Error: {res.text}")
                except: st.error("No se pudo enviar la notificación.")

# --- TAB: ADMIN ---
if rol == "ADMIN":
    with tabs[tab_list.index("⚙️ Admin")]:
        st.header("⚙️ Centro de Administración")
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.divider()
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Sistema CMSG - Desarrollado por C&S Asociados Ltda.")