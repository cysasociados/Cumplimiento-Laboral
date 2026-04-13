import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN Y ESTILO
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# URL DEL APPS SCRIPT (Puente a Drive)
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs DE GOOGLE SHEETS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DE CARGA Y LIMPIEZA TOTAL ---
@st.cache_data(ttl=30)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        # NORMALIZACIÓN TOTAL: Todo a mayúsculas y sin espacios
        df.columns = [str(c).strip().upper() for c in df.columns]
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Portal Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty and 'CLAVE' in df_u.columns:
                match = df_u[df_u['CLAVE'] == pwd.strip().upper()]
                if not match.empty:
                    u = match.iloc[0]
                    st.session_state["authenticated"] = True
                    st.session_state["u_nom"] = u.get('NOMBRE', 'USUARIO')
                    st.session_state["u_rol"] = u.get('ROL', 'USUARIO')
                    st.session_state["u_emp"] = u.get('EMPRESA', '')
                    st.rerun()
                else: st.error("❌ Clave incorrecta")
    st.stop()

# --- 3. DATOS MAESTROS ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    anio = st.selectbox("Año de Análisis", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "HOJA 1")

# --- 4. ESTRUCTURA DE 4 PESTAÑAS (EL HILO CONDUCTOR) ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Laboral", "⚙️ Log de Transacciones"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Laboral"])
else:
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: AVANCE LABORAL ---
with tabs[0]:
    if not df_av.empty:
        meses_lista = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
        cols_m = [c for c in df_av.columns if c in meses_lista]
        
        mes_sel = st.sidebar.selectbox("Seleccione Mes:", ["AÑO COMPLETO"] + cols_m)
        df_f = df_av[df_av['EMPRESA'] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av

        st.header(f"Gestión de Cumplimiento - {anio}")
        
        # INDICADORES (KPIs)
        datos_kpi = df_f[cols_m] if mes_sel == "AÑO COMPLETO" else df_f[[mes_sel]]
        cumple_v = (datos_kpi == "5").sum().sum() + (datos_kpi == 5).sum().sum()
        total_v = datos_kpi.isin([1,2,3,4,5,"1","2","3","4","5"]).sum().sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas Auditadas", len(df_f))
        k2.metric("Certificados OK", int(cumple_v))
        k3.metric("% Avance Real", f"{(cumple_v/total_v*100 if total_v > 0 else 0):.1f}%")

        # CONTEO POR ESTADOS
        st.subheader("📊 Conteo Detallado de Estados")
        c1, c2, c3, c4, c5 = st.columns(5)
        # Forzamos conversión a numérico para contar bien
        df_num = datos_kpi.apply(pd.to_numeric, errors='coerce')
        c1.metric("✅ Cumple", int((df_num == 5).sum().sum()))
        c2.metric("🔵 Revisión", int((df_num == 2).sum().sum()))
        c3.metric("🟡 Obs.", int((df_num == 3).sum().sum()))
        c4.metric("🟠 Carga", int((df_num == 1).sum().sum()))
        c5.metric("🔴 No Cumple", int((df_num == 4).sum().sum()))

        st.divider()

        # GRÁFICO DE BARRAS EVOLUCIÓN
        mapa_n = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple"}
        col_m = {"Carga":"#FF8C00", "Revisión":"#1E90FF", "Obs":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00"}
        
        if rol != "USUARIO":
            st.subheader("📈 Evolución Mensual del Grupo")
            res_evo = []
            for m in cols_m:
                counts = pd.to_numeric(df_f[m], errors='coerce').value_counts()
                for val, cant in counts.items():
                    if val in mapa_n: res_evo.append({'Mes': m, 'Estado': mapa_n[val], 'Cantidad': cant})
            if res_evo:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=col_m, barmode='stack'), use_container_width=True)

        st.divider()

        # DETALLE Y PDF
        emp_sel = st.selectbox("Empresa:", sorted(df_f['EMPRESA'].unique())) if rol != "USUARIO" else st.session_state["u_emp"]
        row_e = df_f[df_f['EMPRESA'] == emp_sel].iloc[0]
        
        ca, cb = st.columns([2, 1])
        with ca:
            st.subheader("📝 Hallazgos")
            obs_col = 'OBS_AUDITORIA' if 'OBS_AUDITORIA' in df_f.columns else 'OBS_AUDITORIA'
            st.warning(row_e[obs_col] if obs_col in row_e and pd.notna(row_e[obs_col]) else "Sin observaciones.")
            
        with cb:
            st.subheader("📄 Certificado")
            if mes_sel == "AÑO COMPLETO": st.info("Elija un mes.")
            else:
                match = df_id[df_id['EMPRESA'] == emp_sel]
                if not match.empty and 'ID_CARPETA' in df_id.columns:
                    id_f = str(match['ID_CARPETA'].iloc[0]).strip()
                    if id_f and id_f != 'NAN' and len(id_f) > 10:
                        mm = str(meses_lista.index(mes_sel) + 1).zfill(2)
                        nombre_pdf = f"Certificado.{mm}{anio}"
                        if st.button(f"🔍 Buscar PDF {mes_sel}"):
                            with st.spinner("Buscando..."):
                                r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_f}")
                                if r.text.startswith("http"):
                                    st.success("¡Encontrado!")
                                    st.link_button("📥 Descargar", r.text.strip())
                                    st.session_state["log_accesos"].append({"FECHA": datetime.now().strftime("%d/%m/%Y"), "USUARIO": st.session_state["u_nom"], "ACCION": f"Descarga {emp_sel} {mes_sel}"})
                                else: st.warning("⚠️ Certificado No Disponible")
                    else: st.error("Falta ID de carpeta.")
                else: st.error("Empresa no vinculada.")

        # GRÁFICO CIRCULAR (PIE CHART)
        st.divider()
        st.subheader(f"🟢 Distribución de Estados: {emp_sel}")
        pie_data = []
        for m in (cols_m if mes_sel == "AÑO COMPLETO" else [mes_sel]):
            val = pd.to_numeric(row_e[m], errors='coerce')
            pie_data.append({'Estado': mapa_n.get(val, "S/I")})
        st.plotly_chart(px.pie(pd.DataFrame(pie_data), names='Estado', hole=.4, color='Estado', color_discrete_map=col_map), use_container_width=True)

# --- TAB 2: BASE IDS ---
if rol != "USUARIO":
    with tabs[1]:
        st.header("🏢 Base Maestra de Empresas")
        st.dataframe(df_id, use_container_width=True)

# --- TAB 3: MASA LABORAL ---
with (tabs[2] if rol != "USUARIO" else tabs[1]):
    st.header("👥 Gestión de Masa Laboral")
    mes_m = st.sidebar.selectbox("Mes Masa:", meses_lista)
    df_masa = cargar_datos(ID_COLABORADORES, f"{mes_m.capitalize()}{anio[-2:]}")
    if not df_masa.empty:
        df_mf = df_masa[df_masa['RAZON_SOCIAL'] == st.session_state["u_emp"]] if rol == "USUARIO" else df_masa
        st.metric("Dotación Total", len(df_mf))
        st.plotly_chart(px.pie(df_mf, names='GENERO', hole=0.4, title="Distribución Género"), use_container_width=True)
    else: st.info("No hay datos de masa cargados.")

# --- TAB 4: LOG ---
if rol == "ADMIN":
    with tabs[3]:
        st.header("⚙️ Log de Transacciones")
        if st.session_state["log_accesos"]: st.table(pd.DataFrame(st.session_state["log_accesos"]))

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")