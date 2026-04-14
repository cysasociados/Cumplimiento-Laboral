import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")

# --- CABECERA CON LOGOS INSTITUCIONALES ---
col_l, col_m, col_r = st.columns([2, 4, 1])
with col_l:
    if os.path.exists("CMSG.png"):
        st.image("CMSG.png", width=250)
    else: st.subheader("🏢 Minera San Gerónimo")

with col_r:
    if os.path.exists("cys.png"):
        st.image("cys.png", width=120)
    else: st.write("**C&S Asociados**")

# --- CONEXIÓN DRIVE (Tu URL Actualizada) ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbyUHcZmDK0ASAYNgjOFa_MIG56WUX6V3JpRVAABUjFPQ-sKCeAdOCQ60jgvAG-uINgIMg/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# CONFIGURACIÓN DE MAPAS
MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Carga Doc.":"#FF8C00", "En Revision":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = next((c for c in df_u.columns if 'CLAVE' in c), 'CLAVE')
            match = df_u[df_u[col_c].astype(str).str.strip() == pwd]
            if not match.empty:
                u = match.iloc[0]
                st.session_state["log_accesos"].append({
                    "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Hora": datetime.now().strftime("%H:%M:%S"),
                    "Usuario": u.get('NOMBRE',''),
                    "Empresa": u.get('EMPRESA',''),
                    "Rol": u.get('ROL','')
                })
                st.session_state.update({"authenticated": True, "u_nom": u.get('NOMBRE',''), "u_rol": u.get('ROL',''), "u_emp": u.get('EMPRESA','')})
                st.rerun()
            else: st.error("❌ Clave no válida.")
    st.stop()

# --- 3. SIDEBAR (FILTROS) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    anio_global = st.selectbox("Año", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MAPA_MESES_CARPETAS.keys()] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    st.divider()
    st.write(f"👤 **{st.session_state['u_nom']}**")
    st.caption(f"Rol: {st.session_state['u_rol']}")
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# --- 4. TABS (4 PARA ADMIN, 2 PARA USUARIO) ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores", "⚙️ Administración"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Colaboradores"])
else:
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: AVANCE + PASARELA DE CARGA ---
with tabs[0]:
    df_id = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in c), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        
        periodo_txt = f"{mes_sidebar} {anio_global}" if mes_sidebar != "AÑO COMPLETO" else f"ANUAL {anio_global}"
        st.header(f"Gestión de Control Laboral CMSG - {periodo_txt}")

        # --- PASARELA DE CARGA (Opción A) ---
        with st.expander("📤 PASARELA DE CARGA DE DOCUMENTOS"):
            if mes_sidebar == "AÑO COMPLETO":
                st.warning("Seleccione un mes en el panel lateral para habilitar la carga.")
            else:
                empresa_up = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa para Carga:", sorted(df_f[col_e].unique()))
                docs_up = [
                    ("Liquidaciones de Sueldos", "LIQ"),
                    ("Planilla Leyes Sociales (Previred)", "PREVIRED"),
                    ("Formulario F30 (Antecedentes)", "F30"),
                    ("Formulario F30-1 (Cumplimiento)", "F30_1"),
                    ("Comprobante de Pagos", "PAGOS"),
                    ("Otros Documentos", "OTROS")
                ]
                
                for nombre_doc, prefijo in docs_up:
                    c_file, c_btn = st.columns([3, 1])
                    arch = c_file.file_uploader(f"Subir {nombre_doc}", type=["pdf"], key=f"up_{prefijo}")
                    if c_btn.button(f"🚀 Enviar {prefijo}", key=f"btn_{prefijo}"):
                        if arch:
                            match = df_id[df_id[col_e].str.contains(empresa_up[:10], case=False, na=False)]
                            if not match.empty:
                                col_f = next((c for c in df_id.columns if 'ID' in c or 'CARPETA' in c), 'IDCARPETA')
                                id_folder = str(match.iloc[0][col_f]).strip()
                                
                                # Preparar nombre y datos
                                nombre_f = f"{prefijo}_{mes_sidebar}_{anio_global}_{empresa_up[:10].replace(' ','_')}.pdf"
                                b64 = base64.b64encode(arch.read()).decode('utf-8')
                                
                                payload = {
                                    "nombre_final": nombre_f,
                                    "id_carpeta": id_folder,
                                    "anio": anio_global,
                                    "mes_nombre": MAPA_MESES_CARPETAS[mes_sidebar],
                                    "mimetype": "application/pdf",
                                    "archivo_base64": b64
                                }
                                
                                with st.spinner(f"Enviando {nombre_doc}..."):
                                    try:
                                        # IMPORTANTE: Usamos 'data' para enviar como formulario, evitando JSON y errores 413
                                        r = requests.post(URL_APPS_SCRIPT, data=payload, timeout=30)
                                        if "✅" in r.text:
                                            st.success(f"¡{nombre_doc} cargado exitosamente!")
                                            st.balloons()
                                        else: st.error(f"Error de Drive: {r.text}")
                                    except: st.error("Fallo de conexión con el servidor.")
                            else: st.error("Carpeta no encontrada para esta empresa.")
                        else: st.warning("Por favor, seleccione un archivo.")

        # --- KPIs Y VISUALIZACIÓN ---
        st.divider()
        cols_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else [c for c in df_f.columns if c in MAPA_MESES_CARPETAS.keys()]
        df_num = df_f[cols_filt].apply(pd.to_numeric, errors='coerce')
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        t_p = df_num.isin([1,2,3,4,5]).sum().sum()
        t_5 = (df_num == 5).sum().sum()
        k2.metric("% Cumplimiento", f"{(t_5/t_p*100 if t_p > 0 else 0):.1f}%")
        al_dia = ((df_num == 5).all(axis=1)).sum() if not df_num.empty else 0
        k3.metric("Empresas al Día", al_dia)

        st.write("### 📊 Resumen de Estados por Periodo")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Cumple", int((df_num == 5).sum().sum()))
        c2.metric("🔵 En Revisión", int((df_num == 2).sum().sum()))
        c3.metric("🟠 Carga Doc.", int((df_num == 1).sum().sum()))
        c4.metric("🟡 Observado", int((df_num == 3).sum().sum()))

        if rol != "USUARIO":
            st.divider()
            st.subheader("📈 Evolución Mensual del Cumplimiento")
            res_evo = []
            for m in [c for c in df_f.columns if c in MAPA_MESES_CARPETAS.keys()]:
                counts = df_f[m].value_counts()
                for cod, cant in counts.items():
                    if pd.notna(cod):
                        res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', 
                                       color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

# --- TAB 2: KPIs EMPRESAS ---
if rol != "USUARIO":
    with tabs[1]:
        st.header("🏢 Registro de Empresas y Carpetas")
        st.dataframe(cargar_datos(ID_EMPRESAS, "HOJA1"), use_container_width=True)

# --- TAB 3: MASA COLABORADORES ---
idx_masa = 2
with tabs[idx_masa]:
    st.header(f"Análisis de Dotación - {anio_global}")
    mes_masa = st.selectbox("Mes Masa:", list(MAPA_MESES_CARPETAS.keys()), key="masa_s")
    df_masa = cargar_datos(ID_COLABORADORES, f"{mes_masa.capitalize()}{anio_global[-2:]}")
    if not df_masa.empty:
        col_rs = next((c for c in df_masa.columns if 'RAZON' in c), df_masa.columns[0])
        df_mf = df_masa[df_masa[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_masa
        
        # Alertas de Estabilidad
        col_con = next((c for c in df_mf.columns if 'CONTRATO' in c), None)
        if col_con:
            pf = df_mf[df_mf[col_con].astype(str).str.contains("PLAZO FIJO", case=False, na=False)]
            if not pf.empty:
                st.warning(f"🚨 Se detectaron {len(pf)} contratos a Plazo Fijo.")
                st.dataframe(pf, use_container_width=True)
            else: st.success("✅ Todo el personal analizado tiene contrato Indefinido.")
        
        m1, m2 = st.columns(2)
        m1.metric("Dotación Total", len(df_mf))
        if 'NACIONALIDAD' in df_mf.columns:
            ext = len(df_mf[~df_mf['NACIONALIDAD'].str.contains('CHILE', na=False)])
            m2.metric("Extranjeros", ext)
        st.dataframe(df_mf, use_container_width=True)

# --- TAB 4: ADMINISTRACIÓN ---
if rol == "ADMIN":
    with tabs[3]:
        st.header("⚙️ Administración")
        st.subheader("📅 Log de Accesos")
        if st.session_state["log_accesos"]:
            st.table(pd.DataFrame(st.session_state["log_accesos"]))
        st.divider()
        st.subheader("👥 Usuarios del Sistema")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

# --- PIE DE PÁGINA ---
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real - C & S Asociados Ltda. para CMSG")