import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs DE GOOGLE SHEETS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DE CARGA CON ULTRA-LIMPIEZA ---
def normalizar_texto(t):
    if pd.isna(t): return ""
    return re.sub(r'[^A-Z0-9]', '', str(t).upper().strip())

@st.cache_data(ttl=10)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        # Limpiamos nombres de columnas de inmediato (Espacios y Mayúsculas)
        df.columns = [str(c).strip().upper() for c in df.columns]
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
        st.title("🔐 Portal Auditoría CMSG")
        pwd = st.text_input("Ingrese su Clave:", type="password")
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                # Buscamos la columna de clave sea cual sea su nombre exacto
                col_clave = [c for c in df_u.columns if "CLAVE" in c or "PASS" in c][0]
                match = df_u[df_u[col_clave].astype(str).str.strip().str.upper() == pwd.strip().upper()]
                if not match.empty:
                    u = match.iloc[0]
                    st.session_state["authenticated"] = True
                    st.session_state["u_nom"] = u.get('NOMBRE', 'USUARIO')
                    st.session_state["u_rol"] = u.get('ROL', 'USUARIO')
                    st.session_state["u_emp"] = u.get('EMPRESA', '')
                    st.rerun()
                else: st.error("❌ Clave incorrecta")
    st.stop()

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    anio = st.selectbox("Año de Análisis", ["2026", "2025"])
    if st.button("Actualizar Datos"): st.cache_data.clear()
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "HOJA 1")

# --- 4. LAS 4 PESTAÑAS ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresa", "👥 Masa Laboral", "⚙️ Log"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresa", "👥 Masa Laboral"])
else:
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: AVANCE (CON INDICADORES Y GRÁFICOS) ---
with tabs[0]:
    if not df_av.empty:
        # Detectamos qué columnas de meses existen realmente
        meses_posibles = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
        cols_m = [c for c in df_av.columns if c in meses_posibles]
        
        mes_sel = st.sidebar.selectbox("Periodo:", ["AÑO COMPLETO"] + cols_m)
        df_f = df_av[df_av['EMPRESA'].astype(str).str.upper().str.strip() == str(st.session_state["u_emp"]).upper().strip()] if rol == "USUARIO" else df_av

        st.header(f"Gestión de Cumplimiento - {anio}")
        
        # 📊 KPIs SUPERIORES
        # Evitamos el KeyError usando .get o verificando existencia
        df_kpi_data = df_f[cols_m] if mes_sel == "AÑO COMPLETO" else df_f[[mes_sel]]
        df_num = df_kpi_data.apply(pd.to_numeric, errors='coerce')
        
        cumple_v = (df_num == 5).sum().sum()
        total_v = df_num.isin([1,2,3,4,5]).sum().sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas Auditadas", len(df_f))
        k2.metric("Certificados OK", int(cumple_v))
        k3.metric("% Avance Real", f"{(cumple_v/total_v*100 if total_v > 0 else 0):.1f}%")

        # 📊 CONTEO POR ESTADOS
        st.subheader("Resumen de Estados")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("✅ Cumple", int((df_num == 5).sum().sum()))
        c2.metric("🔵 Revisión", int((df_num == 2).sum().sum()))
        c3.metric("🟡 Obs.", int((df_num == 3).sum().sum()))
        c4.metric("🟠 Carga", int((df_num == 1).sum().sum()))
        c5.metric("🔴 No Cumple", int((df_num == 4).sum().sum()))

        st.divider()

        # 📈 GRÁFICO DE BARRAS
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

        # 🎯 DETALLE Y PDF
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f['EMPRESA'].unique()))
        row_e = df_f[df_f['EMPRESA'] == emp_sel].iloc[0]
        
        ca, cb = st.columns([2, 1])
        with ca:
            st.subheader("📝 Hallazgos")
            # Buscamos la columna OBSERVACIONES o similar
            col_obs = [c for c in df_f.columns if "OBS" in c][0] if any("OBS" in c for c in df_f.columns) else None
            st.warning(row_e[col_obs] if col_obs and pd.notna(row_e[col_obs]) else "Sin observaciones registradas.")
            
        with cb:
            st.subheader("📄 Certificado")
            if mes_sel == "AÑO COMPLETO": st.info("Elija un mes.")
            else:
                # Match blindado con ID_Empresas
                df_id['KEY'] = df_id['EMPRESA'].apply(normalizar_texto)
                match = df_id[df_id['KEY'] == normalizar_texto(emp_sel)]
                col_id = [c for c in df_id.columns if "CARPETA" in c or "ID" in c]
                
                if not match.empty and col_id:
                    id_f = str(match[col_id[0]].iloc[0]).strip()
                    if id_f and len(id_f) > 10:
                        idx_m = str(meses_posibles.index(mes_sel) + 1).zfill(2)
                        nombre_pdf = f"Certificado.{idx_m}{anio}"
                        if st.button(f"🔍 Descargar PDF {mes_sel}"):
                            r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_f}")
                            if r.text.startswith("http"):
                                st.success("¡Encontrado!")
                                st.link_button("📥 Abrir PDF", r.text.strip())
                            else: st.warning("⚠️ El archivo no existe en Drive.")
                    else: st.error("❌ Empresa sin ID de carpeta.")
                else: st.error("❌ Empresa no vinculada.")

        # 🟢 GRÁFICO CIRCULAR
        st.divider()
        st.subheader(f"Distribución de Estados: {emp_sel}")
        pie_data = []
        for m in (cols_m if mes_sel == "AÑO COMPLETO" else [mes_sel]):
            v = pd.to_numeric(row_e[m], errors='coerce')
            pie_data.append({'Estado': mapa_n.get(v, "S/I")})
        st.plotly_chart(px.pie(pd.DataFrame(pie_data), names='Estado', hole=.4, color='Estado', color_discrete_map=col_m), use_container_width=True)

# --- TAB 2, 3 y 4 ---
if rol == "ADMIN":
    with tabs[1]: st.dataframe(df_id)
    with tabs[3]: st.write("Registro de actividad del sistema.")

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")