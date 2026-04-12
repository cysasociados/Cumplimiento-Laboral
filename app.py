import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN Y ESTILO
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

# URL DEL APPS SCRIPT (Puente a Drive)
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs DE GOOGLE SHEETS
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DETECTIVE (EVITAN EL KEYERROR) ---
def limpiar_col(c):
    return re.sub(r'[^A-Z0-9]', '_', str(c).upper().strip())

def encontrar_columna(df, palabra_clave):
    """Busca una columna que contenga la palabra clave (ej: 'EMP' para Empresa)"""
    for col in df.columns:
        if palabra_clave.upper() in col.upper():
            return col
    return None

@st.cache_data(ttl=30)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        # Limpieza inicial de columnas
        df.columns = [c.strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# Inicializar LOG
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
                col_c = encontrar_columna(df_u, "CLAVE") or encontrar_columna(df_u, "PASS")
                if col_c:
                    match = df_u[df_u[col_c].astype(str).str.strip() == pwd.strip()]
                    if not match.empty:
                        u = match.iloc[0]
                        st.session_state["authenticated"] = True
                        st.session_state["u_nom"] = u.get('Nombre', u.get('NOMBRE', 'Usuario'))
                        st.session_state["u_rol"] = u.get('Rol', u.get('ROL', 'USUARIO'))
                        st.session_state["u_emp"] = u.get('Empresa', u.get('EMPRESA', ''))
                        st.session_state["log_accesos"].append({"Fecha": datetime.now().strftime("%d/%m/%Y"), "Hora": datetime.now().strftime("%H:%M:%S"), "Usuario": st.session_state["u_nom"], "Accion": "Login"})
                        st.rerun()
                    else: st.error("❌ Clave incorrecta")
                else: st.error("No se encontró la columna de Clave en el Excel")
    st.stop()

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    anio = st.selectbox("Año de Análisis", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

# Carga de datos
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "Hoja 1")

# --- 4. CONFIGURACIÓN DE PESTAÑAS (HILO CONDUCTOR) ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    t1, t2, t3, t4 = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Laboral", "⚙️ Log de Transacciones"])
elif rol == "REVISOR":
    t1, t2, t3 = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Laboral"])
else:
    t1, t3 = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: AVANCE LABORAL ---
with t1:
    if not df_av.empty:
        # Detectar columnas clave
        col_emp = encontrar_columna(df_av, "EMPRESA")
        meses_abrev = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
        cols_m = [c for c in df_av.columns if c.lower() in meses_abrev]
        
        mes_sel = st.sidebar.selectbox("Mes Filtro:", ["AÑO COMPLETO"] + cols_m)
        
        # Filtrar datos por rol
        df_f = df_av[df_av[col_emp] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        
        st.header(f"Gestión de Cumplimiento - {anio}")
        
        # 📊 INDICADORES SUPERIORES
        datos_periodo = df_f[cols_m if mes_sel == "AÑO COMPLETO" else [mes_sel]]
        cumple = (datos_periodo == 5).sum().sum()
        reales = datos_periodo.isin([1,2,3,4,5]).sum().sum()
        porc_c = (cumple / reales * 100) if reales > 0 else 0
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas Auditadas", len(df_f))
        k2.metric("Certificados OK", int(cumple))
        k3.metric("% Avance Real", f"{porc_c:.1f}%")

        # 📊 CONTEO DE ESTADOS (Métricas rápidas)
        st.subheader("Conteo por Estados")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("✅ Cumple", (datos_periodo == 5).sum().sum())
        c2.metric("🔵 Revisión", (datos_periodo == 2).sum().sum())
        c3.metric("🟡 Obs.", (datos_periodo == 3).sum().sum())
        c4.metric("🟠 Carga", (datos_periodo == 1).sum().sum())
        c5.metric("🔴 No Cumple", (datos_periodo == 4).sum().sum())

        st.divider()

        # 📈 GRÁFICO DE BARRAS (EVOLUCIÓN)
        mapa = {1:"Carga", 2:"Revisión", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"S/I", 9:"N/A"}
        colores = {"Carga":"#FF8C00", "Revisión":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "S/I":"#555555", "N/A":"#8B4513"}
        
        if rol != "USUARIO":
            st.subheader("Evolución Mensual del Grupo")
            resumen = []
            for m in cols_m:
                counts = df_f[m].value_counts()
                for cod, cant in counts.items():
                    resumen.append({'Mes': m.upper(), 'Estado': mapa.get(int(cod), "S/I"), 'Cantidad': cant})
            if resumen:
                st.plotly_chart(px.bar(pd.DataFrame(resumen), x='Mes', y='Cantidad', color='Estado', color_discrete_map=colores, barmode='stack'), use_container_width=True)

        st.divider()

        # 🎯 DETALLE INDIVIDUAL Y PDF
        emp_sel = st.selectbox("Empresa:", sorted(df_f[col_emp].unique())) if rol != "USUARIO" else st.session_state["u_emp"]
        row_emp = df_f[df_f[col_emp] == emp_sel].iloc[0]
        
        col_obs, col_pdf = st.columns([2, 1])
        with col_obs:
            st.subheader("📝 Hallazgos")
            col_o = encontrar_columna(df_av, "OBS")
            st.warning(row_emp[col_o] if col_o and pd.notna(row_emp[col_o]) else "Sin observaciones.")
            
        with col_pdf:
            st.subheader("📄 Certificado")
            if mes_sel == "AÑO COMPLETO":
                st.info("Elija un mes.")
            else:
                # Conexión a Drive
                col_emp_id = encontrar_columna(df_id, "EMPRESA")
                col_folder = encontrar_columna(df_id, "CARPETA")
                match_id = df_id[df_id[col_emp_id].astype(str).str.strip() == str(emp_sel).strip()]
                
                if not match_id.empty and col_folder:
                    id_f = str(match_id[col_folder].iloc[0]).strip()
                    mm = str(meses_abrev.index(mes_sel.lower()) + 1).zfill(2)
                    nombre_pdf = f"Certificado.{mm}{anio}"
                    if st.button(f"🔍 Buscar PDF {mes_sel}"):
                        r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_f}")
                        if r.text.startswith("http"):
                            st.success("Encontrado")
                            st.link_button("📥 Descargar", r.text.strip())
                            st.session_state["log_accesos"].append({"Fecha": datetime.now().strftime("%d/%m/%Y"), "Hora": datetime.now().strftime("%H:%M:%S"), "Usuario": st.session_state["u_nom"], "Accion": f"Descarga {emp_sel} {mes_sel}"})
                        else: st.warning("No Disponible")
                else: st.error("Sin ID de carpeta")

# --- TAB 2: KPIs EMPRESAS ---
if rol != "USUARIO":
    with t2:
        st.header("🏢 Base de Datos Empresas")
        st.dataframe(df_id, use_container_width=True)

# --- TAB 3: MASA LABORAL ---
with t3:
    st.header("👥 Masa Laboral")
    mes_masa = st.sidebar.selectbox("Mes Masa:", ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'])
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_masa}{anio[-2:]}")
    if not df_m.empty:
        col_rs = encontrar_columna(df_m, "RAZON")
        df_mf = df_m[df_m[col_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m
        st.metric("Dotación", len(df_mf))
        st.plotly_chart(px.pie(df_mf, names=encontrar_columna(df_mf, "GENERO") or df_mf.columns[0]), use_container_width=True)

# --- TAB 4: LOG ---
if rol == "ADMIN":
    with t4:
        st.header("⚙️ Log de Transacciones")
        if st.session_state["log_accesos"]:
            st.table(pd.DataFrame(st.session_state["log_accesos"]))

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")