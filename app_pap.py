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
# 🎨 PERSONALIZACIÓN DE COLORES (CSS)
# ==========================================
COLOR_FONDO_PRINCIPAL = "#A60000"
COLOR_BARRA_LATERAL = "#262730"

estilos_css = f"""
<style>
    .stApp {{ background-color: {COLOR_FONDO_PRINCIPAL}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_BARRA_LATERAL}; }}
    [data-testid="stMetricValue"], h1, h2, h3, p, li {{ color: white !important; }}
    .vega-embed svg text {{ fill: white !important; }}
    .streamlit-expanderHeader {{ background-color: #262730; color: white; }}
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# ==========================================
# 📖 DICCIONARIO INTELIGENTE
# ==========================================
DICCIONARIO_CORRECTO = {
    # INFRAESTRUCTURA
    "diseno arquitectonico": "Diseño arquitectónico",
    "diseño arquitectonico": "Diseño arquitectónico",
    "arquitectonico": "Diseño arquitectónico", 
    "arquitectura": "Diseño arquitectónico",
    "planos": "Diseño arquitectónico",
    "mantenimiento": "Mantenimiento",
    "teatrales": "Productos teatrales",
    "productos": "Productos teatrales",
    "producto": "Productos teatrales",
    # GESTIÓN
    "administracion": "Administración", "admin": "Administración",
    "financiamiento": "Financiamiento", "finanza": "Financiamiento",
    "vinculacion": "Vinculación", "vinc": "Vinculación",
    "gestion": "Gestión", "gestión": "Gestión",
    # COMUNICACIÓN
    "comunicacion": "Comunicación", "comunica": "Comunicación",
    "diseno": "Diseño", "diseño": "Diseño",
    "grafico": "Diseño",
    "difusion": "Difusión", "difucion": "Difusión", "dufusion": "Difusión",
    "memoria": "Memoria/Archivo", "archivo": "Memoria/Archivo",
    # INVESTIGACIÓN
    "investigacion": "Investigación", "investigasion": "Investigación"
}

def normalizar_comparacion(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    if texto in ["nan", "none", ""]: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_textos(texto_sucio):
    if pd.isna(texto_sucio): return ""
    texto_str = str(texto_sucio).strip()
    if texto_str in ["", "nan", "None", "NaN"]: return ""
    palabras = [p.strip() for p in texto_str.split(',')]
    palabras_corregidas = []
    for p in palabras:
        p_norm = normalizar_comparacion(p)
        encontrado = False
        for error_clave, correccion_perfecta in DICCIONARIO_CORRECTO.items():
            if error_clave in p_norm: 
                palabras_corregidas.append(correccion_perfecta)
                encontrado = True
                break 
        if not encontrado:
            palabras_corregidas.append(p.strip()) 
    return ", ".join(sorted(list(dict.fromkeys(palabras_corregidas))))

# ==========================================
# 🔗 CONFIGURACIÓN SISTEMA
# ==========================================
LOGO_URL = "https://github.com/cascaservices2018-maker/app-pap-2026./blob/main/cedramh3-removebg-preview.png?raw=true"
CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]
SUBCATEGORIAS_SUGERIDAS = [
    "Administración", "Financiamiento", "Vinculación", 
    "Memoria/archivo CEDRAM", "Memoria/archivo PAP", "Diseño", "Difusión", 
    "Diseño arquitectónico", "Mantenimiento", "Productos teatrales"
]

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=5)
        if not df.empty: 
            df.columns = df.columns.str.strip() 
            if "Periodo" in df.columns:
                df["Periodo"] = df["Periodo"].astype(str).str.strip().str.title()
        return df
    except: return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
    except Exception as e: st.error(f"Error al guardar: {e}")

# --- FUNCIÓN DE GRÁFICAS DINÁMICAS ---
def graficar_multiformato(df, x_col, y_col, titulo, tipo_grafica, color_base="#FF4B4B"):
    if df.empty:
        st.caption("Sin datos para graficar.")
        return

    if tipo_grafica == "Barras":
        chart = alt.Chart(df).mark_bar(color=color_base, cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(
            x=alt.X(x_col, title=None, sort='-y', axis=alt.Axis(labelColor='white', labelAngle=-45)),
            y=alt.Y(y_col, title="Total", axis=alt.Axis(labelColor='white', gridColor='#444444')),
            tooltip=[x_col, y_col]
        )
    else:
        # Configuración para Pastel y Donut
        radio_interno = 60 if tipo_grafica == "Donut" else 0
        chart = alt.Chart(df).mark_arc(innerRadius=radio_interno, outerRadius=120, stroke="#262730", strokeWidth=2).encode(
            theta=alt.Theta(field=y_col, type="quantitative"),
            color=alt.Color(field=x_col, type="nominal", legend=alt.Legend(title=titulo, labelColor='white', titleColor='white')),
            order=alt.Order(field=y_col, sort="descending"),
            tooltip=[x_col, y_col]
        )
    
    st.altair_chart(chart.properties(height=350).configure_view(stroke='transparent'), theme="streamlit", use_container_width=True)

# --- VARIABLES DE ESTADO ---
if "form_seed" not in st.session_state: st.session_state.form_seed = 0
if "proy_recien_creado" not in st.session_state: st.session_state.proy_recien_creado = None
if "df_buffer_masivo" not in st.session_state: st.session_state.df_buffer_masivo = None
if "last_selected_project" not in st.session_state: st.session_state.last_selected_project = None
if "stats_download" not in st.session_state: st.session_state.stats_download = {}
# Estado para Pestaña 3
if "p3_buffer_proy" not in st.session_state: st.session_state.p3_buffer_proy = None
if "p3_buffer_ent" not in st.session_state: st.session_state.p3_buffer_ent = None
if "p3_filter_hash" not in st.session_state: st.session_state.p3_filter_hash = ""

# --- SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=280) 
    st.markdown("### ⚙️ Panel de Control")
    st.info("Sistema de Gestión de Proyectos PAP - 2026")
    st.markdown("---")
    st.write("Bienvenido al sistema colaborativo.")

col_logo, col_titulo = st.columns([2, 8])
with col_logo: st.image(LOGO_URL, width=170) 
with col_titulo: st.title("Base de datos PAP PERIODOS 2019-2026")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["1. Registrar", "2. Carga Masiva", "3. 📝 Buscar/Editar", "4. 📊 Gráficas", "5. 📥 Descargas", "6. Glosario"])

# ==========================================
# PESTAÑA 1: REGISTRO
# ==========================================
with tab1:
    st.subheader("Nuevo Proyecto")
    with st.form("form_proyecto", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        semilla = st.session_state.form_seed
        anio = c1.number_input("Año", 2019, 2030, datetime.now().year, key=f"anio_{semilla}")
        periodo = c2.selectbox("Periodo", ["Primavera", "Verano", "Otoño"], key=f"periodo_{semilla}")
        cats = c3.multiselect("Categoría(s)", CATEGORIAS_LISTA, key=f"cats_{semilla}")
        nombre = st.text_input("Nombre del Proyecto", key=f"nombre_{semilla}")
        desc = st.text_area("Descripción", key=f"desc_{semilla}")
        ce, cc = st.columns(2)
        num_ent = ce.number_input("Estimado Entregables", 1, step=1, key=f"num_{semilla}")
        comen = cc.text_area("Comentarios", key=f"comen_{semilla}")

        if st.form_submit_button("💾 Guardar Proyecto"):
            if not nombre: st.error("⚠️ El nombre es obligatorio.")
            elif not cats: st.error("⚠️ Elige categoría.")
            else:
                df = load_data("Proyectos")
                if not df.empty and "Nombre del Proyecto" in df.columns and nombre in df["Nombre del Proyecto"].values:
                    st.warning("⚠️ Ya existe.")
                else:
                    nuevo = {"Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre, "Descripción": desc, "Num_Entregables": num_ent, "Categoría": limpiar_textos(", ".join(cats)), "Comentarios": comen, "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    save_data(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True), "Proyectos")
                    st.success("¡Guardado!")
                    st.session_state.proy_recien_creado = nombre
                    st.session_state.form_seed += 1
                    time.sleep(1); st.rerun()

# ==========================================
# PESTAÑA 2: CARGA MASIVA (BÚNKER)
# ==========================================
with tab2:
    st.subheader("⚡ Carga Rápida y Edición")
    st.info("💡 **Modo Búnker:** La tabla NO se actualizará hasta que presiones 'Guardar Cambios'.")
    
    df_p = load_data("Proyectos")
    if not df_p.empty and "Nombre del Proyecto" in df_p.columns:
        lista_proy = sorted(df_p["Nombre del Proyecto"].unique().tolist())
        idx_defecto = 0
        if st.session_state.proy_recien_creado in lista_proy:
            idx_defecto = lista_proy.index(st.session_state.proy_recien_creado)
            
        proy_sel = st.selectbox("Selecciona Proyecto:", lista_proy, index=idx_defecto, key="selector_masivo")
        
        info = df_p[df_p["Nombre del Proyecto"] == proy_sel].iloc[0]
        cat, estim = info.get("Categoría", "General"), int(info.get("Num_Entregables", 5))
        st.caption(f"Categoría: {cat} | Espacios: {estim}")

        if st.session_state.last_selected_project != proy_sel:
            df_e = load_data("Entregables")
            exist = df_e[df_e["Proyecto_Padre"] == proy_sel] if not df_e.empty else pd.DataFrame()
            if not exist.empty:
                temp_df = exist[["Entregable", "Contenido", "Subcategoría", "Plantillas"]].rename(columns={"Entregable": "Nombre", "Subcategoría": "Subcategorías", "Plantillas": "Plantillas_Usadas"})
            else:
                temp_df = pd.DataFrame("", index=range(estim), columns=["Nombre", "Contenido", "Subcategorías", "Plantillas_Usadas"])
            st.session_state.df_buffer_masivo = temp_df.fillna("").astype(str)
            st.session_state.last_selected_project = proy_sel

        with st.form(key=f"form_masivo_{proy_sel}"):
            edited_df = st.data_editor(
                st.session_state.df_buffer_masivo, 
                num_rows="dynamic", 
                use_container_width=True, # Compatibilidad
                column_config={
                    "Subcategorías": st.column_config.TextColumn("Subcategoría(s)", help=f"Opciones: {', '.join(SUBCATEGORIAS_SUGERIDAS)}"),
                    "Nombre": st.column_config.TextColumn("Nombre", required=True),
                    "Contenido": st.column_config.TextColumn("Contenido", width="large")
                }
            )
            submit_btn = st.form_submit_button("🚀 Guardar Cambios")

        if submit_btn:
            df_final = edited_df.astype(str).replace({"nan": "", "None": "", "NaN": ""})
            validos = df_final[df_final["Nombre"].str.strip() != ""].copy()
            if validos.empty: st.error("Tabla vacía.")
            else:
                try:
                    validos["Subcategorías"] = validos["Subcategorías"].apply(limpiar_textos)
                    df_m = load_data("Entregables")
                    if not df_m.empty: df_m = df_m[df_m["Proyecto_Padre"] != proy_sel]
                    
                    nuevos = []
                    hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for _, r in validos.iterrows():
                        nuevos.append({
                            "Proyecto_Padre": proy_sel, 
                            "Entregable": r["Nombre"], 
                            "Contenido": r["Contenido"], 
                            "Categoría": cat, 
                            "Subcategoría": r["Subcategorías"], 
                            "Plantillas": r["Plantillas_Usadas"], 
                            "Fecha_Registro": hoy
                        })
                    save_data(pd.concat([df_m, pd.DataFrame(nuevos)], ignore_index=True), "Entregables")
                    st.session_state.df_buffer_masivo = df_final
                    st.success("¡Guardado!")
                    time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# ==========================================
# PESTAÑA 3: BÚSQUEDA Y EDICIÓN (CASCADA)
# ==========================================
with tab3:
    st.header("📝 Edición de Base de Datos")
    st.info("💡 **Filtros en Cascada:** Selecciona de izquierda a derecha.")
    
    df_p3 = load_data("Proyectos"); df_e3 = load_data("Entregables")
    
    if not df_p3.empty:
        # Pre-limpieza
        if "Categoría" in df_p3.columns: df_p3["Categoría"] = df_p3["Categoría"].apply(limpiar_textos)
        if not df_e3.empty: df_e3["Subcategoría"] = df_e3["Subcategoría"].apply(limpiar_textos)

        # CASCADA LÓGICA
        df_embudo = df_p3.copy()
        
        c0, c1, c2, c3, c4 = st.columns(5)
        
        # 1. Año
        with c1:
            f_ano = st.multiselect("Año:", sorted(df_p3["Año"].unique()), key="f3_ano")
            if f_ano: df_embudo = df_embudo[df_embudo["Año"].isin(f_ano)]
            
        # 2. Periodo (Depende de Año)
        with c2:
            f_per = st.multiselect("Periodo:", sorted(df_embudo["Periodo"].unique()), key="f3_per")
            if f_per: df_embudo = df_embudo[df_embudo["Periodo"].isin(f_per)]
            
        # 3. Categoría (Depende de Año + Periodo)
        with c3:
            cats_disp = set()
            for c in df_embudo["Categoría"].dropna(): cats_disp.update([limpiar_textos(x) for x in str(c).split(',')])
            f_cat = st.multiselect("Categoría:", sorted(list(cats_disp)), key="f3_cat")
            if f_cat: df_embudo = df_embudo[df_embudo["Categoría"].apply(lambda x: any(limpiar_textos(c) in f_cat for c in str(x).split(',')))]
            
        # 4. Subcategoría (Depende de todo lo anterior)
        with c4:
            subs_disp = set()
            if not df_e3.empty:
                # Proyectos visibles hasta ahora
                proys_visibles = df_embudo["Nombre del Proyecto"].unique()
                ents_visibles = df_e3[df_e3["Proyecto_Padre"].isin(proys_visibles)]
                for s in ents_visibles["Subcategoría"].dropna(): 
                    subs_disp.update([limpiar_textos(x) for x in str(s).split(',')])
            
            f_sub = st.multiselect("Subcategoría:", sorted(list(subs_disp)), key="f3_sub")
            if f_sub and not df_e3.empty:
                ents_final = df_e3[df_e3["Subcategoría"].apply(lambda x: any(limpiar_textos(s) in f_sub for s in str(x).split(',')))]
                proys_con_sub = ents_final["Proyecto_Padre"].unique()
                df_embudo = df_embudo[df_embudo["Nombre del Proyecto"].isin(proys_con_sub)]

        # 5. Proyecto Final
        with c0:
            f_nom = st.multiselect("🔍 Proyecto:", sorted(df_embudo["Nombre del Proyecto"].unique()), key="f3_nom")
            if f_nom: df_embudo = df_embudo[df_embudo["Nombre del Proyecto"].isin(f_nom)]

        # --- BÚNKER DE MEMORIA P3 ---
        filter_hash = f"{f_ano}{f_nom}{f_per}{f_cat}{f_sub}"
        
        if st.session_state.p3_filter_hash != filter_hash or st.session_state.p3_buffer_proy is None:
            st.session_state.p3_buffer_proy = df_embudo.copy()
            if not df_e3.empty:
                df_ent_filtered = df_e3[df_e3["Proyecto_Padre"].isin(df_embudo["Nombre del Proyecto"].unique())]
                st.session_state.p3_buffer_ent = df_ent_filtered.copy()
            else:
                st.session_state.p3_buffer_ent = pd.DataFrame()
            st.session_state.p3_filter_hash = filter_hash

        with st.expander(f"📂 Proyectos ({len(st.session_state.p3_buffer_proy)})", expanded=True):
            ed_p = st.data_editor(
                st.session_state.p3_buffer_proy, 
                use_container_width=True, 
                key="ed_p3_p",
                num_rows="fixed",
                column_config={
                    "Categoría": st.column_config.TextColumn("Categoría(s)"),
                    "Año": st.column_config.NumberColumn("Año", format="%d", step=1, required=True),
                    "Periodo": st.column_config.SelectboxColumn("Periodo", options=["Primavera", "Verano", "Otoño"], required=True)
                }
            )
            if st.button("💾 Actualizar Proyectos"):
                if "Categoría" in ed_p.columns: ed_p["Categoría"] = ed_p["Categoría"].apply(limpiar_textos)
                df_m = load_data("Proyectos"); df_m.update(ed_p); save_data(df_m, "Proyectos")
                st.session_state.p3_buffer_proy = ed_p; st.success("✅ Actualizado.")

        with st.expander("📦 Entregables", expanded=True):
            if not st.session_state.p3_buffer_ent.empty:
                ed_e = st.data_editor(
                    st.session_state.p3_buffer_ent, 
                    use_container_width=True, 
                    key="ed_p3_e",
                    column_config={"Subcategoría": st.column_config.TextColumn("Subcategoría")}
                )
                if st.button("💾 Actualizar Entregables"):
                    if "Subcategoría" in ed_e.columns: ed_e["Subcategoría"] = ed_e["Subcategoría"].apply(limpiar_textos)
                    df_m = load_data("Entregables"); df_m.update(ed_e); save_data(df_m, "Entregables")
                    st.session_state.p3_buffer_ent = ed_e; st.success("✅ Actualizado.")
            else: st.info("Sin datos.")

# ==========================================
# PESTAÑA 4: GRÁFICAS (SELECTOR DE TIPO)
# ==========================================
with tab4:
    st.header("📊 Estadísticas en Vivo")
    
    # --- SELECTOR DE TIPO DE GRÁFICA ---
    tipo_g = st.radio("🎨 Estilo de Gráfica:", ["Barras", "Pastel", "Donut"], horizontal=True)
    st.markdown("---")

    df_pg = load_data("Proyectos"); df_eg = load_data("Entregables")
    
    if not df_pg.empty and "Año" in df_pg.columns:
        # Pre-limpieza
        if "Categoría" in df_pg.columns: df_pg["Categoría"] = df_pg["Categoría"].apply(limpiar_textos)
        if not df_eg.empty: df_eg["Subcategoría"] = df_eg["Subcategoría"].apply(limpiar_textos)

        # Filtros Gráficos
        c1, c2, c3, c4 = st.columns(4)
        yg = c1.multiselect("Año", sorted(df_pg["Año"].unique()), default=sorted(df_pg["Año"].unique()), key="g_y")
        pg = c2.multiselect("Periodo", ["Primavera", "Verano", "Otoño"], key="g_p")
        cg = c3.multiselect("Categoría", CATEGORIAS_LISTA, key="g_c")
        sg = c4.multiselect("Subcategoría", sorted(SUBCATEGORIAS_SUGERIDAS), key="g_s")

        df_f = df_pg.copy()
        if yg: df_f = df_f[df_f["Año"].isin(yg)]
        if pg: df_f = df_f[df_f["Periodo"].astype(str).str.strip().isin(pg)]
        if cg: df_f = df_f[df_f["Categoría"].apply(lambda x: any(c in str(x) for c in cg))]

        if not df_f.empty:
            # 1. EVOLUCIÓN ANUAL (SIEMPRE BARRAS AGRUPADAS)
            st.subheader("📅 Evolución Anual")
            pa = df_f["Año"].value_counts().reset_index(); pa.columns=["Año","Total"]; pa["Tipo"]="Proyectos"
            ea = pd.DataFrame()
            if not df_eg.empty:
                vis = df_f["Nombre del Proyecto"].unique()
                ev = df_eg[df_eg["Proyecto_Padre"].isin(vis)]
                if not ev.empty:
                    mapa = df_f.set_index("Nombre del Proyecto")["Año"].to_dict()
                    ev["Año_R"] = ev["Proyecto_Padre"].map(mapa)
                    ea = ev["Año_R"].value_counts().reset_index(); ea.columns=["Año","Total"]; ea["Tipo"]="Entregables"
            
            df_chart = pd.concat([pa, ea])
            if not df_chart.empty:
                evol_chart = alt.Chart(df_chart).encode(
                    x=alt.X('Año:O', axis=alt.Axis(title='Año', labelAngle=0, labelColor='white')),
                    y=alt.Y('Total:Q', axis=alt.Axis(title='Cantidad', labelColor='white', gridColor='#444444')),
                    color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Proyectos', 'Entregables'], range=['#FF4B4B', '#FFD700']), legend=alt.Legend(title=None, labelColor='white', orient='top'))
                ).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(xOffset='Tipo:N').properties(height=350).configure_view(stroke='transparent')
                st.altair_chart(evol_chart, use_container_width=True)

            # 2. DISTRIBUCIONES (DINÁMICAS)
            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Por Periodo")
                dp = df_f["Periodo"].value_counts().reset_index(); dp.columns=["Periodo", "Total"]
                graficar_multiformato(dp, "Periodo", "Total", "Periodo", tipo_g, "#FFFFFF")
            with col_b:
                st.subheader("Por Categoría")
                sc = df_f["Categoría"].str.split(',').explode().str.strip(); sc = sc[sc!=""]; sc=sc[sc!="nan"]
                dc = sc.value_counts().reset_index(); dc.columns=["Categoría", "Total"]
                graficar_multiformato(dc, "Categoría", "Total", "Categoría", tipo_g, "#E0E0E0")
            
            st.markdown("---")
            st.subheader("📦 Distribución de Subcategorías")
            if not df_eg.empty:
                vis = df_f["Nombre del Proyecto"].unique()
                ev = df_eg[df_eg["Proyecto_Padre"].isin(vis)]
                if not ev.empty:
                    ss = ev["Subcategoría"].str.split(',').explode().str.strip(); ss = ss[ss!=""]; ss=ss[ss!="nan"]
                    ds = ss.value_counts().reset_index(); ds.columns=["Subcategoría", "Total"]
                    graficar_multiformato(ds, "Subcategoría", "Total", "Subcategoría", tipo_g, "#CCCCCC")
            
            st.session_state.stats_download = {"Resumen": df_chart, "Periodo": dp, "Categoría": dc}

# ==========================================
# PESTAÑA 5: DESCARGAS
# ==========================================
with tab5:
    st.header("📥 Descargas")
    if st.button("Generar Excel"):
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine='openpyxl') as w: 
            load_data("Proyectos").to_excel(w, 'Proyectos', index=False)
            load_data("Entregables").to_excel(w, 'Entregables', index=False)
        st.download_button("⬇️ Descargar BD.xlsx", b.getvalue(), "Respaldo_Completo.xlsx")

# ==========================================
# PESTAÑA 6: GLOSARIO
# ==========================================
with tab6:
    st.header("📖 Glosario")
    st.markdown("""
    **Gestión:** Dirección | **Comunicación:** Mensajes | **Infraestructura:** Instalaciones | **Investigación:** Historia.
    """)
