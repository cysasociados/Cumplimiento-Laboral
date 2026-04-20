import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz
import time

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CORPORATIVOS (CSS)
# ==============================================================================
st.set_page_config(
    page_title="Control de Cumplimiento Laboral CMSG", 
    layout="wide", 
    page_icon="🛡️"
)
chile_tz = pytz.timezone('America/Santiago')

# Inyección de CSS de Alta Fidelidad (Sin recortes para mantener la estética CMSG)
st.markdown("""
    <style>
    /* Ocultar etiquetas de peso predeterminadas de Streamlit */
    [data-testid="stFileUploaderInstructions"] div { display: none !important; }
    .stFileUploader section div div { display: none !important; }
    .stFileUploader section div { padding-top: 5px !important; }
    
    /* Contenedores de información y tarjetas */
    .caja-instrucciones {
        background-color: #f8f9fa; 
        padding: 25px; 
        border-radius: 15px; 
        border: 1px solid #dee2e6;
        margin-bottom: 20px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Botones Maestros de Acción */
    .stButton > button { 
        width: 100%; 
        border-radius: 12px; 
        font-weight: 800; 
        height: 3.8em;
        text-transform: uppercase;
        transition: 0.3s ease all;
    }
    
    /* Indicadores KPI de gran tamaño */
    [data-testid="stMetricValue"] { 
        font-size: 38px; 
        color: #1E90FF; 
        font-weight: 900; 
    }

    /* Tarjetas cuantitativas por estado (Dashboard) */
    .metric-card {
        text-align: center;
        padding: 12px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        margin-bottom: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# CONFIGURACIÓN DE CONEXIONES Y BASES DE DATOS (IDs REALES)
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbwt9t5vQBsijY4eI9yF-sI82ctU5HGuW8xE2WVPwUBjOvaqGSGh7bi1DZaazU7NQEavfA/exec"
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# CONFIGURACIÓN DE RECURSOS HUMANOS Y CAUSALES
CAUSALES_LEGALES = [
    "Art. 159 N°1: Mutuo acuerdo", "Art. 159 N°2: Renuncia voluntaria",
    "Art. 159 N°4: Vencimiento de plazo", "Art. 159 N°5: Conclusión de servicio",
    "Art. 160: Conductas indebidas", "Art. 161: Necesidades de la empresa",
    "Traslado de Faena / Anexo Contrato"
]

# MAPEO DE ESTADOS DE AUDITORÍA
MAPA_ESTADOS = {
    1: "Carga Doc.", 2: "En Revision", 3: "Observado", 
    4: "No Cumple", 5: "Cumple", 8: "Sin Info", 9: "No Corresp."
}

COLORES_ESTADOS = {
    "Cumple": "#00FF00", "No Cumple": "#FF0000", "Observado": "#FFFF00", 
    "En Revision": "#1E90FF", "Carga Doc.": "#FF8C00", "Sin Info": "#555555", 
    "No Corresp.": "#8B4513"
}

MESES_LISTA = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARP = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

# ==============================================================================
# 2. FUNCIONES DE SOPORTE (LÓGICA EXPLÍCITA)
# ==============================================================================
def validar_rut(rut):
    """Algoritmo de validación de RUT chileno."""
    rut = str(rut).replace(".", "").replace("-", "").upper().strip()
    if not re.match(r"^\d{7,8}[0-9K]$", rut): return False
    cuerpo, dv = rut[:-1], rut[-1]
    suma = 0; multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    dvr = 11 - (suma % 11)
    dvr = 'K' if dvr == 10 else '0' if dvr == 11 else str(dvr)
    return dv == dvr

@st.cache_data(ttl=300)
def cargar_datos(sheet_id, hoja):
    """Carga de datos desde Google Sheets vía consulta CSV."""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={hoja}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# ==============================================================================
# 3. SISTEMA DE ACCESO (LOGIN)
# ==============================================================================
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
    with c_l2:
        if os.path.exists("CMSG.png"): st.image("CMSG.png", width=220)
        st.title("Portal Cumplimiento Laboral CMSG")
        pwd_inp = st.text_input("Ingrese su Contraseña:", type="password").strip()
        if st.button("Ingresar al Portal", use_container_width=True):
            df_usuarios = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_usuarios.empty:
                col_clave = next((c for c in df_usuarios.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_usuarios[df_usuarios[col_clave].astype(str).str.strip() == pwd_inp]
                if not match.empty:
                    u_data = match.iloc[0]
                    st.session_state.update({
                        "authenticated": True, "u_nom": u_data.get('NOMBRE',''), 
                        "u_rol": u_data.get('ROL',''), "u_emp": u_data.get('EMPRESA',''), 
                        "u_email": u_data.get('EMAIL','')
                    })
                    st.rerun()
                else: st.error("Acceso denegado: Credenciales inválidas.")
    st.stop()

# ==============================================================================
# 4. SIDEBAR Y CONFIGURACIÓN DE FILTROS GLOBALES
# ==============================================================================
with st.sidebar:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", use_container_width=True)
    st.markdown(f"👤 **Usuario:** {st.session_state['u_nom']}")
    st.markdown(f"🏢 **Empresa:** {st.session_state['u_emp']}")
    st.markdown("---")
    anio_sel = st.selectbox("Año de Gestión", ["2026", "2025"])
    
    # Mejora: Refresco manual para actualizar datos del Excel
    if st.button("🔄 ACTUALIZAR DATOS"):
        st.cache_data.clear()
        st.rerun()

    df_av_global = cargar_datos(ID_AVANCE, anio_sel)
    cols_meses = [c for c in df_av_global.columns if c in MESES_LISTA] if not df_av_global.empty else []
    mes_filt = st.selectbox("Periodo de Análisis", ["AÑO COMPLETO"] + cols_meses)
    
    st.markdown("---")
    if st.button("🚪 CERRAR SESIÓN"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

rol_u = st.session_state["u_rol"]
if rol_u == "USUARIO":
    nombres_tabs = ["📉 Dashboard", "📤 Carga Mensual", "👥 Colaboradores EECC"]
else:
    nombres_tabs = ["📉 Dashboard", "📊 KPIS Empresas", "📤 Carga Mensual", "👥 Colaboradores EECC", "⚙️ Admin"]

tabs = st.tabs(nombres_tabs)

# ==============================================================================
# 5. TAB 1: DASHBOARD (MÉTRICAS Y FILTRO ESTADO 9)
# ==============================================================================
with tabs[nombres_tabs.index("📉 Dashboard")]:
    df_empresas_ids = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av_global.empty:
        col_emp_nombre = next((c for c in df_av_global.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_dash = df_av_global[df_av_global[col_emp_nombre] == st.session_state["u_emp"]] if rol_u == "USUARIO" else df_av_global
        cols_periodo = [mes_filt] if mes_filt != "AÑO COMPLETO" else cols_meses
        
        # --- LÓGICA DE CUMPLIMIENTO REAL (EXCLUYENDO EL 9) ---
        df_num_dash = df_dash[cols_periodo].apply(pd.to_numeric, errors='coerce')
        df_audit_dash = df_num_dash.copy()
        df_audit_dash[df_audit_dash == 9] = pd.NA # El estado 9 no afecta el promedio
        
        total_eval = df_audit_dash.count().sum()
        total_5 = (df_audit_dash == 5).sum().sum()
        perc_real = (total_5 / total_eval * 100) if total_eval > 0 else 0
        
        # --- KPI EXCELENCIA: EECC CON 100% CUMPLIMIENTO (ESTADO 5) ---
        def chequear_100_cumple(row):
            obligaciones = row[row.isin([1, 2, 3, 4, 5, 8])]
            if obligaciones.empty: return False
            return (obligaciones == 5).all()
        
        conteo_excelencia = df_num_dash.apply(chequear_100_cumple, axis=1).sum()

        st.header(f"Seguimiento de Cumplimiento - {mes_filt} {anio_sel}")
        
        # Fila de KPIs Principales
        m1, m2, m3 = st.columns(3)
        m1.metric("EECC en el Sistema", len(df_dash))
        m2.metric("% Cumplimiento Real", f"{perc_real:.1f}%")
        m3.metric("EECC 100% Cumple", int(conteo_excelencia))

        st.divider()
        st.subheader("📊 Documentos por Estado")
        
        # --- TARJETAS CUANTITATIVAS (SIN EL ESTADO 9 - 6 COLUMNAS) ---
        conteo_estados = df_num_dash.stack().value_counts()
        c_cards = st.columns(6) 
        lista_estados_ver = [1, 2, 3, 4, 5, 8]
        
        for i, cod_est in enumerate(lista_estados_ver):
            nom_est = MAPA_ESTADOS.get(cod_est)
            cant_est = int(conteo_estados.get(cod_est, 0))
            color_est = COLORES_ESTADOS.get(nom_est, "#555555")
            c_cards[i].markdown(f"""
                <div class='metric-card' style='background-color:{color_est};'>
                    <div style='font-size:11px;'>{nom_est.upper()}</div>
                    <div style='font-size:24px;'>{cant_est}</div>
                </div>
            """, unsafe_allow_html=True)

        if mes_filt == "AÑO COMPLETO":
            st.write("### 📈 Evolución Mensual de Estados")
            data_evo = []
            for m_evo in cols_meses:
                cnts = df_dash[m_evo].value_counts()
                for cod_e, cant_e in cnts.items():
                    if pd.notna(cod_e) and int(cod_e) != 9:
                        data_evo.append({'Mes': m_evo, 'Estado': MAPA_ESTADOS.get(int(cod_e)), 'Cantidad': cant_e})
            if data_evo:
                st.plotly_chart(px.bar(pd.DataFrame(data_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()
        emp_analisis = st.selectbox("Analizar Empresa Individual:", sorted(df_dash[col_emp_nombre].unique()))
        df_emp_especifica = df_dash[df_dash[col_emp_nombre] == emp_analisis]
        col_graf, col_cert = st.columns([3, 1.2])
        
        with col_graf:
            # Gráfico Circular de la empresa seleccionada (Sin estado 9)
            p_data = df_emp_especifica[cols_meses].stack().value_counts().reset_index()
            p_data.columns = ['Cod', 'Cant']
            p_data = p_data[p_data['Cod'] != 9]
            p_data['Estado'] = p_data['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(p_data, values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Distribución Estatus: {emp_analisis}"), use_container_width=True)
            
            # Semáforo histórico de 12 meses
            st.write("#### 📜 Semáforo Histórico (Estatus Mensual)")
            m_g1, m_g2 = cols_meses[:6], cols_meses[6:]
            def dibujar_semaforo(lista_m):
                cols_sem = st.columns(6)
                for idx, mes_s in enumerate(lista_m):
                    val_s = int(df_emp_especifica[mes_s].values[0]) if pd.notna(df_emp_especifica[mes_s].values[0]) else 8
                    txt_s = MAPA_ESTADOS.get(val_s); bg_s = COLORES_ESTADOS.get(txt_s, "#555"); tc_s = "#000" if txt_s in ["Observado", "Cumple", "En Revision"] else "#FFF"
                    cols_sem[idx].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:8px; border-radius:8px; background-color:{bg_s}; color:{tc_s}; min-height:65px; display:flex; flex-direction:column; justify-content:center;'><b style='font-size:11px;'>{mes_s}</b><br><span style='font-size:8px; font-weight:bold;'>{txt_s.upper()}</span></div>", unsafe_allow_html=True)
            dibujar_semaforo(m_g1); st.write(""); dibujar_semaforo(m_g2)

        with col_cert:
            st.subheader("📄 Certificado")
            mes_c = st.selectbox("Seleccione Mes:", cols_meses, key="mes_cert_v60")
            if st.button("Consultar Certificado", use_container_width=True):
                match_c = df_empresas_ids[df_empresas_ids['EMPRESA'].str.contains(emp_analisis[:10], case=False, na=False)]
                if not match_c.empty:
                    id_carp = str(match_c.iloc[0]['IDCARPETA']).strip()
                    nom_archivo = f"Certificado.{MAPA_MESES_NUM[mes_c]}{anio_sel}.pdf"
                    res_c = requests.get(URL_APPS_SCRIPT, params={"nombre": nom_archivo, "carpeta": id_carp})
                    if res_c.text.startswith("http"):
                        st.session_state["link_pdf_v60"] = res_c.text.strip()
            if "link_pdf_v60" in st.session_state:
                st.link_button("📥 Descargar Certificado", st.session_state["link_pdf_v60"], use_container_width=True)

# ==============================================================================
# 6. TAB 2: KPIS EMPRESAS (INTELIGENCIA BASADA EN LOG Y LIBROS)
# ==============================================================================
if rol_u != "USUARIO":
    with tabs[nombres_tabs.index("📊 KPIS Empresas")]:
        st.header("📊 Inteligencia de Colaboradores EECC")
        
        # Carga de Log de Dotación y Libros Mensuales
        df_log_dot = cargar_datos(ID_COLABORADORES, "Log_Dotacion")
        # Hoja del mes seleccionado (ej: ENE26)
        nombre_hoja_mes = f"{mes_filt}{anio_sel[2:]}" if mes_filt != "AÑO COMPLETO" else None
        df_libro_mes = cargar_datos(ID_COLABORADORES, nombre_hoja_mes) if nombre_hoja_mes else pd.DataFrame()

        if not df_log_dot.empty:
            st.write("### 📈 Dinámica de Movimientos (Ingresos, Finiquitos y Traslados)")
            
            # Filtro por Empresa para KPIs
            eecc_filt = st.multiselect("Filtrar por EECC:", sorted(df_log_dot[df_log_dot.columns[1]].unique()))
            df_kpi_log = df_log_dot[df_log_dot[df_log_dot.columns[1]].isin(eecc_filt)] if eecc_filt else df_log_dot
            
            k_c1, k_c2, k_c3, k_c4 = st.columns(4)
            altas = len(df_kpi_log[df_kpi_log[df_kpi_log.columns[2]].str.contains("Alta", na=False)])
            bajas = len(df_kpi_log[df_kpi_log[df_kpi_log.columns[2]].str.contains("Baja", na=False)])
            traslados = len(df_kpi_log[df_kpi_log[df_kpi_log.columns[6]].str.contains("Traslado", na=False)])
            
            k_c1.metric("Nuevos Ingresos", altas)
            k_c2.metric("Finiquitos", bajas, delta_color="inverse")
            k_c3.metric("Traslados Faena", traslados)
            k_c4.metric("Dotación Neta", altas - bajas)
            
            st.divider()

            # Sección de Género (Viene de los Libros Mensuales ENE26, FEB26...)
            if not df_libro_mes.empty:
                st.write(f"### 👥 Radiografía de Dotación: {nombre_hoja_mes}")
                col_gen = next((c for c in df_libro_mes.columns if 'GEN' in str(c).upper()), None)
                if col_gen:
                    g_col1, g_col2 = st.columns([1, 2])
                    with g_col1:
                        c_gen = df_libro_mes[col_gen].value_counts().reset_index()
                        c_gen.columns = ['Género', 'Cantidad']
                        st.plotly_chart(px.pie(c_gen, values='Cantidad', names='Género', title="Distribución de Género", color_discrete_sequence=["#FF69B4", "#1E90FF"]), use_container_width=True)
                    with g_col2:
                        col_eecc_lib = next((c for c in df_libro_mes.columns if 'EMP' in str(c).upper()), df_libro_mes.columns[1])
                        st.plotly_chart(px.bar(df_libro_mes, x=col_eecc_lib, color=col_gen, title="Hombres vs Mujeres por Empresa", barmode='group'), use_container_width=True)
                else:
                    st.warning(f"La hoja {nombre_hoja_mes} no contiene la columna 'GENERO'.")
            else:
                st.info("Seleccione un Mes específico en el sidebar para visualizar la demografía del Libro.")

            st.write("### 📜 Detalle de Movimientos Registrados")
            st.dataframe(df_kpi_log.sort_values(by=df_kpi_log.columns[0], ascending=False), use_container_width=True)
        else:
            st.info("No hay datos de movimientos aún.")

# ==============================================================================
# 7. TAB 3: CARGA MENSUAL (8 BLOQUES EXPLÍCITOS - SIN COMPRIMIR)
# ==============================================================================
with tabs[nombres_tabs.index("📤 Carga Mensual")]:
    st.header("📤 Portal de Carga de Documentación")
    if mes_filt == "AÑO COMPLETO":
        st.warning("Seleccione un Mes específico en el sidebar para habilitar la carga.")
    else:
        col_c1, col_c2 = st.columns([1.7, 1.3])
        with col_c2:
            st.markdown("""
                <div class='caja-instrucciones'>
                    <h4>📖 Requisitos de Carga</h4>
                    <p style='font-size:14px; color:#d9534f;'><b>MÁXIMO 20MB POR ARCHIVO.</b></p>
                    <ul style='font-size:13px; line-height:1.6;'>
                        <li><b>Liquidaciones:</b> PDF con toda la nómina mensual.</li>
                        <li><b>Comprobantes de Pago:</b> Transferencias Sueldos y Anticipos.</li>
                        <li><b>Previred:</b> Planilla de pago y resumen.</li>
                        <li><b>Libro (LRE):</b> Archivo CSV generado para la DT.</li>
                        <li><b>Comprobante:</b> Envio LRE a DT.</li>
                        <li><b>F30:</b> Certificado con emision no mayor a 10 días.</li>
                        <li><b>F30-1:</b> Certificado solo con trabajadores vigentes en CMSG.</li>
                        <li><b>Planilla:</b> Planilla de Control Mensual Trabajadores Vigentes.</li>
                        <li><b>Al Terminar: Presionar Boton "Finalizar Proceso de Carga".</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
        
        with col_c1:
            emp_carga = st.session_state['u_emp'] if rol_u == "USUARIO" else st.selectbox("EECC a Cargar:", sorted(df_av_global[col_emp_nombre].unique()), key="sel_carga_v60")
            st.divider()
            
            def ejecutar_subida(archivo, prefijo, empresa):
                if archivo and archivo.size <= 20*1024*1024:
                    match_e = df_empresas_ids[df_empresas_ids['EMPRESA'].str.contains(empresa[:10], case=False, na=False)]
                    if not match_e.empty:
                        id_c = str(match_e.iloc[0]['IDCARPETA']).strip()
                        ext = archivo.name.split('.')[-1]
                        payload = {
                            "tipo": "mensual", "id_carpeta": id_c, "anio": anio_sel,
                            "nombre_final": f"{prefijo}_{mes_filt}.{ext}",
                            "mes_nombre": MAPA_MESES_CARP[mes_filt],
                            "archivo_base64": base64.b64encode(archivo.read()).decode('utf-8')
                        }
                        if requests.post(URL_APPS_SCRIPT, data=payload).status_code == 200:
                            st.success(f"✅ {prefijo} subido correctamente.")
            
            # --- LOS 8 BLOQUES DE CARGA EXPLÍCITOS ---
            f1 = st.file_uploader("1. Liquidaciones de Sueldo (PDF)", type=["pdf"], key="f1")
            if st.button("Subir Liquidaciones", key="btn1"): ejecutar_subida(f1, "LIQ", emp_carga)
            
            f2 = st.file_uploader("2. Comprobantes de Pago (PDF)", type=["pdf"], key="f2")
            if st.button("Subir Comprobantes", key="btn2"): ejecutar_subida(f2, "PAGOS", emp_carga)
            
            f3 = st.file_uploader("3. Cotizaciones Previred (PDF)", type=["pdf"], key="f3")
            if st.button("Subir Cotizaciones", key="btn3"): ejecutar_subida(f3, "PREVIRED", emp_carga)
            
            f4 = st.file_uploader("4. Libro Remuneraciones (CSV)", type=["csv"], key="f4")
            if st.button("Subir Libro LRE", key="btn4"): ejecutar_subida(f4, "LIBRO", emp_carga)
            
            f5 = st.file_uploader("5. Comprobante envio LRE a DT (PDF)", type=["pdf"], key="f5")
            if st.button("Subir Comprobante DT", key="btn5"): ejecutar_subida(f5, "DT", emp_carga)
            
            f6 = st.file_uploader("6. Certificado F30 (PDF)", type=["pdf"], key="f6")
            if st.button("Subir F30", key="btn6"): ejecutar_subida(f6, "F30", emp_carga)
            
            f7 = st.file_uploader("7. Certificado F30-1 (PDF)", type=["pdf"], key="f7")
            if st.button("Subir F30-1", key="btn7"): ejecutar_subida(f7, "F301", emp_carga)
            
            f8 = st.file_uploader("8. Planilla de Control Mensual (.XLSX)", type=["xlsx","xls"], key="f8")
            if st.button("Subir Planilla Control", key="btn8"): ejecutar_subida(f8, "CTRL", emp_carga)

            st.divider()
            if st.button("🏁 FINALIZAR CARGA Y NOTIFICAR", key="btn_not_v60", use_container_width=True):
                requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email","empresa":emp_carga,"usuario":st.session_state["u_nom"],"periodo":f"CARGA MENSUAL COMPLETA: {mes_filt}"})
                st.success("Notificación enviada al equipo auditor.")

# ==============================================================================
# 8. TAB 4: COLABORADORES EECC (LÓGICA DUAL DRIVE + EXCEL)
# ==============================================================================
with tabs[nombres_tabs.index("👥 Colaboradores EECC")]:
    st.header("👥 Gestión de Colaboradores EECC")
    t_mov_sel = st.radio("Acción a Registrar:", ["🟢 Alta (Ingreso)", "🔴 Baja (Egreso)"], horizontal=True)
    st.divider()
    
    col_d1, col_d2 = st.columns([1.7, 1.3])
    with col_d2:
        c_dx = "#1E90FF" if "Alta" in t_mov_sel else "#d9534f"
        req_dx = "<li>Contrato de Contrato</li><li>Anexo de Contrato</li><li>Cedula de Identidad</li><li>Certificado de AFP/Salud</li><li>Comprobante Registro Contrato DT</li><li>Comprobante entrega RIOHS</li>" if "Alta" in t_mov_sel else "<li>Finiquito Legalizado + Comprobante de Pago</li><li>Anexo de Traslado de Faena</li>"
        st.markdown(f"<div class='caja-instrucciones' style='border-left: 8px solid {c_dx};'><h4>📌 Requisitos</h4><ul style='font-size:14px;'>{req_dx}</ul></div>", unsafe_allow_html=True)
    
    with col_d1:
        emp_d = st.session_state['u_emp'] if rol_u == "USUARIO" else st.selectbox("EECC Responsable:", sorted(df_av_global[col_emp_nombre].unique()), key="sel_d_v60")
        dx1, dx2 = st.columns(2)
        with dx1: nom_d = st.text_input("Nombre Completo Trabajador:")
        with dx2: rut_d = st.text_input("RUT Trabajador (con guion):")
        
        dx3, dx4 = st.columns(2)
        with dx3: fec_d = st.date_input("Fecha Efectiva:", datetime.now())
        with dx4: cau_d = st.selectbox("Causal / Motivo:", CAUSALES_LEGALES) if "Baja" in t_mov_sel else "Nuevo Ingreso"
        
        st.divider()
        files_d = st.file_uploader("Cargar Documentos de Respaldo (PDFs):", type=["pdf"], accept_multiple_files=True, key="bulk_d_v60")
        
        if st.button("🚀 REGISTRAR MOVIMIENTO", key="btn_reg_dot", use_container_width=True):
            if nom_d and validar_rut(rut_d) and files_d:
                match_d = df_empresas_ids[df_empresas_ids['EMPRESA'].str.contains(emp_d[:10], case=False, na=False)]
                if not match_d.empty:
                    id_cd = str(match_d.iloc[0]['IDCARPETA']).strip()
                    # 1. Guardar archivos físicamente en Drive
                    for arc in files_d:
                        requests.post(URL_APPS_SCRIPT, data={
                            "tipo": "colaborador", "id_carpeta": id_cd, "nombre_persona": nom_d.upper(),
                            "rut": rut_d, "nombre_final": arc.name, 
                            "archivo_base64": base64.b64encode(arc.read()).decode('utf-8')
                        })
                    
                    # 2. REGISTRO DUAL: Envía datos para el Email Y el grabado en la hoja Log_Dotacion
                    res_f = requests.post(URL_APPS_SCRIPT, data={
                        "accion": "enviar_email", "tipo": "colaborador", "empresa": emp_d,
                        "usuario": st.session_state["u_nom"], "movimiento": t_mov_sel,
                        "nombre_persona": nom_d.upper(), "rut": rut_d,
                        "fecha_evento": fec_d.strftime('%d/%m/%Y'), "causal": cau_d,
                        "periodo": f"MOVIMIENTO: {t_mov_sel} - {nom_d.upper()}"
                    })
                    
                    if "Exito" in res_f.text:
                        st.success(f"✅ Registro completado exitosamente en Drive y Base de Datos.")
                    else:
                        st.error(f"⚠️ El archivo se guardó, pero la base de datos reportó un alcance: {res_f.text}")
            else:
                st.warning("Verifique el RUT y asegúrese de subir los documentos.")

# --- ADMIN TAB ---
if rol_u != "USUARIO":
    with tabs[nombres_tabs.index("⚙️ Admin")]:
        st.header("⚙️ Configuración Administrativa")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Control Laboral CMSG | Acorazado v60 | Sergio Edition")