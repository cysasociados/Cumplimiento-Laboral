import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN E INTERFAZ LIMPIA
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

# URL DEL APPS SCRIPT (Puente a Drive)
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs DE GOOGLE SHEETS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DE LIMPIEZA Y CARGA ---
def limpiar_col(c):
    return re.sub(r'[^A-Z0-9]', '_', str(c).upper().strip())

def limpiar_val(v):
    if pd.isna(v): return ""
    return re.sub(r'[^A-Z0-9]', '', str(v).upper().strip())

@st.cache_data(ttl=60)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        df.columns = [limpiar_col(c) for c in df.columns]
        # Limpieza específica para la columna EMPRESA si existe
        if 'EMPRESA' in df.columns:
            df['EMPRESA'] = df['EMPRESA'].astype(str).str.strip()
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# Inicializar LOG si no existe
if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

# --- 2. SISTEMA DE LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                col_c = next((c for c in df_u.columns if "CLAVE" in c or "PASS" in c), None)
                if col_c:
                    match = df_u[df_u[col_c].astype(str).str.strip() == pwd.strip()]
                    if not match.empty:
                        u = match.iloc[0]
                        # Registro en el LOG
                        st.session_state["log_accesos"].append({
                            "Fecha": datetime.now().strftime("%d/%m/%Y"),
                            "Hora": datetime.now().strftime("%H:%M:%S"),
                            "Usuario": u.get('NOMBRE', 'Usuario'),
                            "Empresa": u.get('EMPRESA', 'CMSG'),
                            "Acción": "Inicio de Sesión"
                        })
                        st.session_state["authenticated"] = True
                        st.session_state["u_nom"] = u.get('NOMBRE', 'Usuario')
                        st.session_state["u_rol"] = u.get('ROL', 'USUARIO')
                        st.session_state["u_emp"] = u.get('EMPRESA', '')
                        st.rerun()
                    else: st.error("❌ Clave incorrecta")
    st.stop()

# --- 3. DISEÑO DE BARRA LATERAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    st.caption(f"Rol: {st.session_state['u_rol']}")
    anio = st.selectbox("Año de Análisis", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# Carga de datos base
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "Hoja 1")

if df_av.empty:
    st.error("No se pudieron cargar los datos de Avance. Verifica los archivos.")
    st.stop()

# --- 4. DEFINICIÓN DE PESTAÑAS (MANTENIENDO EL HILO CONDUCTOR) ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    t1, t2, t3, t4 = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Laboral", "⚙️ Log de Transacciones"])
elif rol == "REVISOR":
    t1, t2, t3 = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Laboral"])
else: # USUARIO
    t1, t3 = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: AVANCE LABORAL (EL CORAZÓN DEL SISTEMA) ---
with t1:
    meses_id = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
    cols_m = [c for c in meses_id if c in df_av.columns]
    
    with st.sidebar:
        st.divider()
        mes_sel = st.selectbox("Mes de Análisis:", ["AÑO COMPLETO"] + cols_m)

    st.header(f"Gestión de Cumplimiento Laboral - {anio}")
    
    # 📊 INDICADORES SUPERIORES (KPIs)
    df_f = df_av[df_av['EMPRESA'] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
    datos_periodo = df_f[cols_m if mes_sel == "AÑO COMPLETO" else [mes_sel]]
    
    cumple = (datos_periodo == 5).sum().sum()
    reales = datos_periodo.isin([1,2,3,4,5]).sum().sum()
    porc_c = (cumple / reales * 100) if reales > 0 else 0
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Empresas Auditadas", len(df_f))
    k2.metric("Certificados OK", int(cumple))
    k2.caption(f"De un total de {reales} documentos analizados")
    k3.metric("% Avance Real", f"{porc_c:.1f}%")

    # 📊 CONTEO POR ESTADOS
    st.subheader("📊 Conteo Detallado de Estados")
    ind1, ind2, ind3, ind4, ind5 = st.columns(5)
    ind1.metric("✅ Cumple", (datos_periodo == 5).sum().sum())
    ind2.metric("🔵 Revisión", (datos_periodo == 2).sum().sum())
    ind3.metric("🟡 Observado", (datos_periodo == 3).sum().sum())
    ind4.metric("🟠 Carga", (datos_periodo == 1).sum().sum())
    ind5.metric("🔴 No Cumple", (datos_kpi := (datos_periodo == 4).sum().sum()))

    st.divider()

    # 📈 GRÁFICO DE BARRAS DE EVOLUCIÓN
    mapa = {1:"Carga", 2:"Revisión", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"S/I", 9:"N/A"}
    colores = {"Carga":"#FF8C00", "Revisión":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "S/I":"#555555", "N/A":"#8B4513"}

    if rol != "USUARIO":
        st.subheader("📈 Evolución Mensual del Grupo")
        resumen = []
        for m in cols_m:
            counts = df_f[m].value_counts()
            for cod, cant in counts.items():
                resumen.append({'Mes': m, 'Estado': mapa.get(int(cod), "S/I"), 'Cantidad': cant})
        if resumen:
            fig_bar = px.bar(pd.DataFrame(resumen), x='Mes', y='Cantidad', color='Estado', 
                             color_discrete_map=colores, barmode='stack', height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # 🎯 DETALLE Y BUSCADOR DE PDF
    emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f['EMPRESA'].unique())) if rol != "USUARIO" else st.session_state["u_emp"]
    row_emp = df_f[df_f['EMPRESA'] == emp_sel].iloc[0]
    
    c_hall, c_pdf = st.columns([2, 1])
    with c_hall:
        st.subheader("📝 Hallazgos")
        col_o = next((c for c in df_av.columns if "OBS" in c), None)
        obs_txt = row_emp[col_o] if col_o and pd.notna(row_emp[col_o]) else "Sin observaciones."
        st.warning(f"**Nota de Auditoría:** {obs_txt}")
        
    with c_pdf:
        st.subheader("📄 Certificado")
        if mes_sel == "AÑO COMPLETO":
            st.info("Seleccione un mes para descargar el PDF.")
        else:
            # Lógica de conexión a Drive
            df_id['KEY_LIMPIA'] = df_id['EMPRESA'].apply(limpiar_val)
            match_id = df_id[df_id['KEY_LIMPIA'] == limpiar_val(emp_sel)]
            col_id = next((c for c in df_id.columns if "CARPETA" in c or "ID" in c), None)
            
            if not match_id.empty and col_id:
                id_f = str(match_id[col_id].iloc[0]).strip()
                if id_f and id_f != "nan":
                    idx_m = str(meses_id.index(mes_sel) + 1).zfill(2)
                    nombre_pdf = f"Certificado.{idx_m}{anio}"
                    if st.button(f"🔍 Descargar PDF {mes_sel}"):
                        try:
                            r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_f}", timeout=10)
                            if r.text.startswith("http"):
                                st.success("¡Encontrado!")
                                st.link_button("📥 Abrir Certificado", r.text.strip())
                                # Registrar descarga en el log
                                st.session_state["log_accesos"].append({
                                    "Fecha": datetime.now().strftime("%d/%m/%Y"),
                                    "Hora": datetime.now().strftime("%H:%M:%S"),
                                    "Usuario": st.session_state

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")