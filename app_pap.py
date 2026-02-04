import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import io
import time
import altair as alt
import unicodedata

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión PAP - Nube", 
    layout="wide", 
    page_icon="☁️",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🔗 CONFIGURACIÓN SISTEMA
# ==========================================
LOGO_URL = "https://github.com/cascaservices2018-maker/app-pap-2026./blob/main/cedramh3-removebg-preview.png?raw=true"
CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]
SUBCATEGORIAS_SUGERIDAS = ["Administración", "Financiamiento", "Vinculación", "Memoria/archivo CEDRAM", "Diseño", "Difusión", "Diseño arquitectónico", "Mantenimiento", "Productos teatrales"]
ESTATUS_OPCIONES = ["Completado", "En Proceso", "Pendiente", "Pausado", "Cancelado"]

# ==========================================
# 🎨 ESTILOS
# ==========================================
COLOR_FONDO_PRINCIPAL = "#A60000"
COLOR_BARRA_LATERAL = "#262730"

st.markdown(f"""
<style>
    .stApp {{ background-color: {COLOR_FONDO_PRINCIPAL}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_BARRA_LATERAL}; }}
    [data-testid="stMetricValue"], h1, h2, h3, p, li {{ color: white !important; }}
    .vega-embed svg text {{ fill: white !important; }}
    .streamlit-expanderHeader {{ background-color: #262730; color: white; }}
    [data-testid="stMetricLabel"] {{ color: #FFD700 !important; font-weight: bold; font-size: 1.1rem; }}
    [data-testid="stMetricValue"] {{ color: white !important; font-size: 3rem !important; font-weight: 700; }}
    div[data-testid="stButton"] > button:first-child {{ border: 1px solid white; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 📖 FUNCIONES
# ==========================================
DICCIONARIO_CORRECTO = {
    "diseno arquitectonico": "Diseño arquitectónico", "diseño arquitectonico": "Diseño arquitectónico",
    "arquitectonico": "Diseño arquitectónico", "arquitectura": "Diseño arquitectónico",
    "planos": "Diseño arquitectónico", "mantenimiento": "Mantenimiento",
    "teatrales": "Productos teatrales", "productos": "Productos teatrales",
    "producto": "Productos teatrales", "administracion": "Administración", "admin": "Administración",
    "financiamiento": "Financiamiento", "finanza": "Financiamiento",
    "vinculacion": "Vinculación", "vinc": "Vinculación", "gestion": "Gestión",
    "comunicacion": "Comunicación", "comunica": "Comunicación", "diseno": "Diseño", "diseño": "Diseño",
    "grafico": "Diseño", "difusion": "Difusión", "dufusion": "Difusión",
    "memoria": "Memoria/Archivo", "archivo": "Memoria/Archivo", "investigacion": "Investigación"
}

def limpiar_textos(texto_sucio):
    if pd.isna(texto_sucio): return ""
    texto_str = str(texto_sucio).strip()
    if texto_str in ["", "nan", "None", "NaN"]: return ""
    palabras = [p.strip() for p in texto_str.split(',')]
    palabras_corregidas = []
    for p in palabras:
        p_norm = ''.join(c for c in unicodedata.normalize('NFD', str(p).lower()) if unicodedata.category(c) != 'Mn')
        encontrado = False
        for k, v in DICCIONARIO_CORRECTO.items():
            if k in p_norm:
                palabras_corregidas.append(v); encontrado = True; break
        if not encontrado: palabras_corregidas.append(p.strip())
    return ", ".join(sorted(list(dict.fromkeys(palabras_corregidas))))

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0) # TTL 0 para ver cambios inmediatos
        if not df.empty: 
            df.columns = df.columns.str.strip()
            cols_req = ["Estatus", "Responsable", "Observaciones", "Num_Entregables"]
            for c in cols_req:
                if c not in df.columns: df[c] = ""
        return df.fillna("")
    except: return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
    except Exception as e: st.error(f"Error: {e}")

# --- FUNCIÓN GRÁFICA ---
def graficar_multiformato(df, x_col, y_col, titulo, tipo_grafica, color_base="#FF4B4B"):
    if df.empty:
        st.caption("Sin datos.")
        return
    base = alt.Chart(df).encode(tooltip=[x_col, y_col])
    if tipo_grafica == "Barras":
        chart = base.mark_bar(color=color_base, cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X(x_col, title=None, sort='-y', axis=alt.Axis(labelColor='white', labelAngle=-45)),
            y=alt.Y(y_col, title="Total", axis=alt.Axis(labelColor='white', gridColor='#444444'))
        ).properties(height=350)
    else:
        chart = base.mark_arc(innerRadius=70 if tipo_grafica == "Donut" else 0, outerRadius=120, stroke="#262730").encode(
            theta=alt.Theta(field=y_col, type="quantitative"),
            color=alt.Color(field=x_col, type="nominal", legend=alt.Legend(title=titulo, labelColor='white')),
            order=alt.Order(field=y_col, sort="descending")
        ).properties(height=350)
    st.altair_chart(chart.configure_view(stroke='transparent'), theme="streamlit", use_container_width=True)

# --- VARIABLES ---
if "form_seed" not in st.session_state: st.session_state.form_seed = 0
if "proy_recien_creado" not in st.session_state: st.session_state.proy_recien_creado = None
if "df_buffer_masivo" not in st.session_state: st.session_state.df_buffer_masivo = None
if "last_selected_project" not in st.session_state: st.session_state.last_selected_project = None
if "p3_buffer_proy" not in st.session_state: st.session_state.p3_buffer_proy = None
if "p3_buffer_ent" not in st.session_state: st.session_state.p3_buffer_ent = None
if "p3_filter_hash" not in st.session_state: st.session_state.p3_filter_hash = ""
if "stats_download" not in st.session_state: st.session_state.stats_download = {}

# --- SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=280) 
    st.markdown("### ⚙️ Panel de Control")
    st.info("Sistema de Gestión de Proyectos PAP - 2026")
    st.markdown("---")

col_logo, col_titulo = st.columns([2, 8])
with col_logo: st.image(LOGO_URL, width=170) 
with col_titulo: st.title("Base de datos PAP PERIODOS 2019-2026")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["1. Registrar", "2. Carga Masiva", "3. 📝 Buscar/Editar/Borrar", "4. 📊 Gráficas", "5. 📥 Descargas", "6. Glosario"])

# ==========================================
# PESTAÑA 1: REGISTRO
# ==========================================
with tab1:
    st.subheader("Nuevo Proyecto")
    key_form = f"form_{st.session_state.form_seed}"
    with st.form(key_form):
        c1, c2, c3 = st.columns(3)
        anio = c1.number_input("Año", 2019, 2030, datetime.now().year)
        periodo = c2.selectbox("Periodo", ["Primavera", "Verano", "Otoño"])
        cats = c3.multiselect("Categoría(s)", CATEGORIAS_LISTA)
        nombre = st.text_input("Nombre del Proyecto")
        desc = st.text_area("Descripción")
        ce, cc = st.columns(2)
        num_ent = ce.number_input("Estimado Entregables", 1, 50, 5)
        comen = cc.text_area("Comentarios")
        
        if st.form_submit_button("💾 Guardar Proyecto"):
            if not nombre: st.error("Falta nombre.")
            else:
                df = load_data("Proyectos")
                if not df.empty and nombre in df["Nombre del Proyecto"].values:
                    st.warning("Ya existe.")
                else:
                    nuevo = {"Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre, "Descripción": desc, "Num_Entregables": num_ent, "Categoría": limpiar_textos(", ".join(cats)), "Comentarios": comen, "Fecha_Registro": datetime.now().strftime("%Y-%m-%d")}
                    save_data(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True), "Proyectos")
                    st.session_state.proy_recien_creado = nombre
                    st.session_state.form_seed += 1
                    st.success(f"Creado '{nombre}'. Ve a Carga Masiva.")
                    time.sleep(1); st.rerun()

# ==========================================
# PESTAÑA 2: CARGA MASIVA
# ==========================================
with tab2:
    st.subheader("⚡ Carga Rápida")
    df_p = load_data("Proyectos")
    if not df_p.empty:
        lista_proy = sorted(df_p["Nombre del Proyecto"].unique().tolist())
        idx_sel = 0
        if st.session_state.proy_recien_creado in lista_proy:
            idx_sel = lista_proy.index(st.session_state.proy_recien_creado)
        
        proy_sel = st.selectbox("Proyecto:", lista_proy, index=idx_sel, key="sm")
        
        info = df_p[df_p["Nombre del Proyecto"] == proy_sel].iloc[0]
        cat, num_filas = info.get("Categoría", "General"), int(info.get("Num_Entregables", 5))
        
        if st.session_state.last_selected_project != proy_sel:
            df_e = load_data("Entregables")
            exist = df_e[df_e["Proyecto_Padre"] == proy_sel]
            if not exist.empty:
                temp = exist[["Entregable", "Contenido", "Subcategoría"]].rename(columns={"Entregable": "Nombre", "Subcategoría": "Subcategorías"})
            else:
                temp = pd.DataFrame("", index=range(num_filas), columns=["Nombre", "Contenido", "Subcategorías"])
            st.session_state.df_buffer_masivo = temp.fillna("").astype(str)
            st.session_state.last_selected_project = proy_sel

        with st.form(f"f_{proy_sel}"):
            edited = st.data_editor(st.session_state.df_buffer_masivo, num_rows="dynamic", use_container_width=True,
                column_config={"Subcategorías": st.column_config.TextColumn("Subcategoría", help=f"{', '.join(SUBCATEGORIAS_SUGERIDAS)}"), "Nombre": st.column_config.TextColumn("Nombre", required=True)})
            if st.form_submit_button("🚀 Guardar"):
                val = edited.astype(str).replace({"nan": ""})
                val = val[val["Nombre"].str.strip() != ""]
                val["Subcategorías"] = val["Subcategorías"].apply(limpiar_textos)
                df_m = load_data("Entregables")
                if not df_m.empty: df_m = df_m[df_m["Proyecto_Padre"] != proy_sel]
                nuevos = []
                hoy = datetime.now().strftime("%Y-%m-%d")
                for _, r in val.iterrows():
                    nuevos.append({"Proyecto_Padre": proy_sel, "Entregable": r["Nombre"], "Contenido": r["Contenido"], "Categoría": cat, "Subcategoría": r["Subcategorías"], "Estatus": "Pendiente", "Responsable": "", "Observaciones": "", "Fecha_Registro": hoy})
                save_data(pd.concat([df_m, pd.DataFrame(nuevos)], ignore_index=True), "Entregables")
                st.session_state.df_buffer_masivo = val
                st.success("Guardado"); time.sleep(1); st.rerun()

# ==========================================
# PESTAÑA 3: EDICIÓN
# ==========================================
with tab3:
    st.header("📝 Edición")
    df_p3 = load_data("Proyectos"); df_e3 = load_data("Entregables")
    if not df_p3.empty:
        if "Categoría" in df_p3.columns: df_p3["Categoría"] = df_p3["Categoría"].apply(limpiar_textos)
        if not df_e3.empty: df_e3["Subcategoría"] = df_e3["Subcategoría"].apply(limpiar_textos)
        
        df_emb = df_p3.copy()
        c1, c2, c3, c4, c0 = st.columns(5)
        fa = c1.multiselect("Año", sorted(df_p3["Año"].unique())); 
        if fa: df_emb = df_emb[df_emb["Año"].isin(fa)]
        fp = c2.multiselect("Periodo", sorted(df_emb["Periodo"].unique())); 
        if fp: df_emb = df_emb[df_emb["Periodo"].isin(fp)]
        fn = c0.multiselect("Proyecto", sorted(df_emb["Nombre del Proyecto"].unique())); 
        if fn: df_emb = df_emb[df_emb["Nombre del Proyecto"].isin(fn)]
        
        h = f"{fa}{fp}{fn}"
        if st.session_state.p3_filter_hash != h or st.session_state.p3_buffer_proy is None:
            st.session_state.p3_buffer_proy = df_emb.copy()
            st.session_state.p3_buffer_ent = df_e3[df_e3["Proyecto_Padre"].isin(df_emb["Nombre del Proyecto"].unique())].copy() if not df_e3.empty else pd.DataFrame()
            st.session_state.p3_filter_hash = h

        with st.expander("Proyectos", expanded=True):
            c_ed, c_del = st.columns([3, 1])
            ed_p = c_ed.data_editor(st.session_state.p3_buffer_proy, use_container_width=True, key="ep3")
            if c_ed.button("💾 Actualizar"): 
                m = load_data("Proyectos"); m.update(ed_p); save_data(m, "Proyectos"); st.success("OK")
            
            p_del = c_del.selectbox("Eliminar:", ["--"] + sorted(st.session_state.p3_buffer_proy["Nombre del Proyecto"].unique()))
            if p_del != "--" and c_del.button("🔥 Borrar"):
                save_data(load_data("Proyectos")[load_data("Proyectos")["Nombre del Proyecto"] != p_del], "Proyectos")
                save_data(load_data("Entregables")[load_data("Entregables")["Proyecto_Padre"] != p_del], "Entregables")
                st.success("Borrado"); time.sleep(1); st.rerun()

        with st.expander("Entregables", expanded=True):
            if not st.session_state.p3_buffer_ent.empty:
                cols = [c for c in ["Entregable", "Contenido", "Subcategoría", "Fecha_Registro"] if c in st.session_state.p3_buffer_ent.columns]
                ed_e = st.data_editor(st.session_state.p3_buffer_ent[cols], use_container_width=True, key="ee3", num_rows="dynamic")
                if st.button("💾 Guardar Entregables"):
                    full = load_data("Entregables")
                    full = full[~full["Proyecto_Padre"].isin(st.session_state.p3_buffer_ent["Proyecto_Padre"].unique())]
                    m = load_data("Entregables"); m.update(ed_e); save_data(m, "Entregables")
                    st.success("OK")

# ==========================================
# PESTAÑA 4: GRÁFICAS
# ==========================================
with tab4:
    st.header("📊 Estadísticas")
    tipo = st.radio("Tipo:", ["Barras", "Pastel"], horizontal=True)
    df_p = load_data("Proyectos"); df_e = load_data("Entregables")
    if not df_p.empty:
        c1, c2 = st.columns(2)
        yg = c1.multiselect("Año", sorted(df_p["Año"].unique()), default=sorted(df_p["Año"].unique()))
        df_f = df_p[df_p["Año"].isin(yg)] if yg else df_p
        
        k1, k2 = st.columns(2)
        k1.metric("Proyectos", len(df_f))
        k2.metric("Entregables", len(df_e[df_e["Proyecto_Padre"].isin(df_f["Nombre del Proyecto"])]))
        
        st.subheader("Por Periodo")
        d = df_f["Periodo"].value_counts().reset_index(); d.columns=["Periodo", "Total"]
        graficar_multiformato(d, "Periodo", "Total", "Periodo", tipo)
        
        # Guardar para descarga
        st.session_state.stats_download = d.to_csv(index=False).encode('utf-8')

# ==========================================
# PESTAÑA 5: DESCARGAS (CON GRÁFICAS)
# ==========================================
with tab5:
    st.header("📥 Descargas")
    if st.button("Generar Excel Completo"):
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine='openpyxl') as w: 
            load_data("Proyectos").to_excel(w, 'Proyectos', index=False)
            load_data("Entregables").to_excel(w, 'Entregables', index=False)
        st.download_button("⬇️ BD.xlsx", b.getvalue(), "Respaldo.xlsx")
    
    if st.session_state.get("stats_download"):
        st.download_button("⬇️ Datos de Gráficas (CSV)", st.session_state.stats_download, "graficas.csv", "text/csv")

# ==========================================
# PESTAÑA 6: GLOSARIO (ORIGINAL)
# ==========================================
with tab6:
    st.header("📖 Glosario de Términos")
    st.markdown("""
    ### 1. Categorías Principales
    * **Gestión:** Incluye todo lo relacionado con la administración, dirección y coordinación de los proyectos.
    * **Comunicación:** Abarca estrategias de difusión, redes sociales, diseño gráfico y mensajes clave.
    * **Infraestructura:** Se refiere a planos, mantenimiento físico, remodelaciones y diseño arquitectónico.
    * **Investigación:** Documentación histórica, análisis de contexto, diagnósticos y memoria del proyecto.

    ### 2. Subcategorías Comunes
    * **Administración:** Trámites, permisos, oficios y control interno.
    * **Financiamiento:** Presupuestos, búsqueda de recursos y reportes financieros.
    * **Vinculación:** Relación con la comunidad, socios formadores y otras instituciones.
    * **Memoria/Archivo:** Organización y resguardo de documentos históricos y entregables pasados.
    * **Diseño:** Creación de identidad visual, carteles, logos y material gráfico.
    * **Difusión:** Publicaciones en prensa, radio, web y redes sociales.
    * **Diseño Arquitectónico:** Planos, renders y propuestas espaciales.
    * **Mantenimiento:** Reportes de estado físico y acciones de reparación.
    * **Productos Teatrales:** Guiones, escaletas y producción escénica.
    """)
