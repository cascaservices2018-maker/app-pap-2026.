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
COLOR_FONDO_PRINCIPAL = "#A60000"  # Rojo Institucional
COLOR_BARRA_LATERAL = "#262730"    # Gris oscuro

estilos_css = f"""
<style>
    .stApp {{
        background-color: {COLOR_FONDO_PRINCIPAL};
    }}
    [data-testid="stSidebar"] {{
        background-color: {COLOR_BARRA_LATERAL};
    }}
    [data-testid="stMetricValue"], h1, h2, h3, p, li {{
        color: white !important;
    }}
    .vega-embed svg text {{
        fill: white !important;
    }}
    .streamlit-expanderHeader {{
        background-color: #262730;
        color: white;
    }}
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# ==========================================
# 📖 DICCIONARIO INTELIGENTE (CORRECTOR)
# ==========================================
DICCIONARIO_CORRECTO = {
    "gestion": "Gestión",
    "gestión": "Gestión",
    "comunicacion": "Comunicación",
    "comunicasion": "Comunicación",
    "comunica": "Comunicación",
    "infraestructura": "Infraestructura",
    "infra": "Infraestructura",
    "investigacion": "Investigación",
    "investigasion": "Investigación",
    "difusion": "Difusión",
    "difucion": "Difusión",
    "vinculacion": "Vinculación",
    "vinc": "Vinculación",
    "financiamiento": "Financiamiento",
    "finanza": "Financiamiento",
    "diseno": "Diseño",
    "diseño": "Diseño",
    "arquitectonico": "Arquitectónico",
    "arquitectura": "Arquitectónico",
    "mantenimiento": "Mantenimiento",
    "teatrales": "Productos teatrales",
    "productos": "Productos teatrales",
    "producto": "Productos teatrales",
    "productos teatrales": "Productos teatrales",
    "memoria": "Memoria/Archivo",
    "archivo": "Memoria/Archivo"
}

def normalizar_comparacion(texto):
    if pd.isna(texto) or texto == "": return ""
    texto = str(texto).lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_textos(texto_sucio):
    if pd.isna(texto_sucio) or str(texto_sucio).strip() == "": return ""
    palabras = [p.strip() for p in str(texto_sucio).split(',')]
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
            palabras_corregidas.append(p.capitalize()) 
    return ", ".join(sorted(list(dict.fromkeys(palabras_corregidas))))

# ==========================================
# 🔗 CONFIGURACIÓN DEL SISTEMA
# ==========================================
LOGO_URL = "https://github.com/cascaservices2018-maker/app-pap-2026./blob/main/cedramh3-removebg-preview.png?raw=true"
CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]
SUBCATEGORIAS_SUGERIDAS = [
    "Financiamiento", "Vinculación", "Memoria/archivo CEDRAM", 
    "Memoria/archivo PAP", "Diseño", "Difusión", 
    "Diseño arquitectónico", "Mantenimiento", "Productos teatrales"
]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=5)
        if not df.empty: df.columns = df.columns.str.strip()
        return df
    except: return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
    except Exception as e: st.error(f"No se pudo guardar: {e}")

def graficar_oscuro(df, x_col, y_col, titulo_x, titulo_y, color_barra="#FFFFFF"):
    chart = alt.Chart(df).mark_bar(color=color_barra).encode(
        x=alt.X(x_col, title=titulo_x, sort='-y'),
        y=alt.Y(y_col, title=titulo_y),
        tooltip=[x_col, y_col]
    ).configure_axis(labelColor='white', titleColor='white', gridColor='#660000').properties(height=300)
    st.altair_chart(chart, use_container_width=True)

# --- INICIALIZACIÓN DE ESTADO ---
if "form_seed" not in st.session_state: st.session_state.form_seed = 0
# Variables para controlar la edición masiva sin reseteos
if "proyecto_activo_masivo" not in st.session_state: st.session_state.proyecto_activo_masivo = None
if "df_buffer_masivo" not in st.session_state: st.session_state.df_buffer_masivo = pd.DataFrame()

# --- INTERFAZ ---
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Registrar PROYECTO", 
    "2. Carga Masiva ENTREGABLES", 
    "3. 📝 Buscar y Editar", 
    "4. 📊 Gráficas", 
    "5. 📥 Descargar Excel",
    "6. 📖 Glosario"
])

# ==========================================
# PESTAÑA 1: REGISTRO (CON RESET INTELIGENTE)
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
            if not nombre: 
                st.error("⚠️ El nombre es obligatorio. (Tus datos siguen aquí, complétalos)")
            elif not cats: 
                st.error("⚠️ Debes elegir al menos una categoría. (Tus datos siguen aquí, complétalos)")
            else:
                df = load_data("Proyectos")
                if not df.empty and "Nombre del Proyecto" in df.columns and nombre in df["Nombre del Proyecto"].values:
                    st.warning("⚠️ Ya existe un proyecto con ese nombre.")
                else:
                    nuevo = {
                        "Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre,
                        "Descripción": desc, "Num_Entregables": num_ent,
                        "Categoría": limpiar_textos(", ".join(cats)),
                        "Comentarios": comen,
                        "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    save_data(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True), "Proyectos")
                    st.success("¡Proyecto guardado con éxito!")
                    st.session_state.form_seed += 1
                    time.sleep(1)
                    st.rerun()

# ==========================================
# PESTAÑA 2: CARGA MASIVA (ESTABILIDAD TOTAL)
# ==========================================
with tab2:
    st.subheader("⚡ Carga Rápida y Edición")
    st.info("💡 **Estabilidad:** Puedes copiar y pegar desde Excel sin que se borren los datos.")
    
    df_p = load_data("Proyectos")
    if df_p.empty: st.warning("Cargando proyectos...")
    elif "Nombre del Proyecto" in df_p.columns:
        proy_sel = st.selectbox("Selecciona el Proyecto:", sorted(df_p["Nombre del Proyecto"].unique().tolist()))
        
        info_p = df_p[df_p["Nombre del Proyecto"] == proy_sel].iloc[0]
        cat_auto = info_p.get("Categoría", "General")
        estimado = int(info_p.get("Num_Entregables", 5))
        st.caption(f"Categoría: **{cat_auto}** | Espacios iniciales: **{estimado}**")

        # --- LÓGICA DE CARGA ÚNICA ---
        # Solo cargamos de la BD si CAMBIAMOS de proyecto. Si es el mismo, usamos la memoria.
        if st.session_state.proyecto_activo_masivo != proy_sel:
            # 1. Cargar datos frescos de la BD
            df_e = load_data("Entregables")
            existentes = pd.DataFrame()
            if not df_e.empty:
                existentes = df_e[df_e["Proyecto_Padre"] == proy_sel]
            
            if not existentes.empty:
                cols_utiles = ["Entregable", "Contenido", "Subcategoría", "Plantillas"]
                datos_carga = existentes[cols_utiles].rename(columns={
                    "Entregable": "Nombre_Entregable",
                    "Subcategoría": "Subcategorías",
                    "Plantillas": "Plantillas_Usadas"
                })
                # Forzamos todo a string para evitar errores al pegar
                st.session_state.df_buffer_masivo = datos_carga.fillna("").astype(str)
            else:
                # Creamos tabla vacía
                st.session_state.df_buffer_masivo = pd.DataFrame(
                    "", 
                    index=range(estimado), 
                    columns=["Nombre_Entregable", "Contenido", "Subcategorías", "Plantillas_Usadas"]
                ).astype(str)
            
            # Actualizamos el puntero del proyecto actual
            st.session_state.proyecto_activo_masivo = proy_sel

        # --- EDITOR CONECTADO A MEMORIA ---
        st.write("👇 **Edita o agrega entregables:**")
        edited_df = st.data_editor(
            st.session_state.df_buffer_masivo, # Siempre leemos del buffer
            num_rows="dynamic",
            key=f"editor_masivo_estable", # Key fija para estabilidad
            use_container_width=True,
            column_config={
                "Subcategorías": st.column_config.TextColumn("Subcategoría(s)", default="General", help=f"Opciones: {', '.join(SUBCATEGORIAS_SUGERIDAS)}"),
                "Nombre_Entregable": st.column_config.TextColumn("Nombre Entregable", required=True),
                "Contenido": st.column_config.TextColumn("Contenido", width="large"),
                "Plantillas_Usadas": st.column_config.TextColumn("Link/Plantilla")
            }
        )
        
        # ACTUALIZACIÓN EN TIEMPO REAL DEL BUFFER (Para soportar pegado y ediciones múltiples)
        if not edited_df.equals(st.session_state.df_buffer_masivo):
            st.session_state.df_buffer_masivo = edited_df

        if st.button("🚀 Guardar Cambios (Reemplazar)"):
            datos_validos = edited_df[edited_df["Nombre_Entregable"].notna() & (edited_df["Nombre_Entregable"] != "")].copy()
            if datos_validos.empty: st.error("La tabla está vacía o no tiene nombres.")
            else:
                try:
                    datos_validos["Subcategorías"] = datos_validos["Subcategorías"].apply(limpiar_textos)
                    df_master = load_data("Entregables")
                    
                    # Limpiamos previos de este proyecto
                    if not df_master.empty:
                        df_master = df_master[df_master["Proyecto_Padre"] != proy_sel]
                    
                    nuevas_filas = []
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    for index, row in datos_validos.iterrows():
                        nuevas_filas.append({
                            "Proyecto_Padre": proy_sel,
                            "Entregable": row["Nombre_Entregable"],
                            "Contenido": row["Contenido"],
                            "Categoría": cat_auto,
                            "Subcategoría": row["Subcategorías"],
                            "Plantillas": row["Plantillas_Usadas"],
                            "Fecha_Registro": fecha_hoy
                        })
                    
                    df_final = pd.concat([df_master, pd.DataFrame(nuevas_filas)], ignore_index=True)
                    save_data(df_final, "Entregables")
                    st.success(f"¡Listo! Se actualizaron {len(nuevas_filas)} entregables.")
                    st.balloons()
                    time.sleep(1)
                    # Forzamos recarga desde cero para asegurar sincronía
                    st.session_state.proyecto_activo_masivo = None 
                    st.rerun()
                except Exception as e: st.error(f"Error al guardar: {e}")

# ==========================================
# PESTAÑA 3: EDICIÓN (AÑO Y PERIODO MODIFICABLES)
# ==========================================
with tab3:
    st.header("📝 Edición de Base de Datos")
    st.info("💡 **Nota:** Datos corregidos automáticamente al visualizar. Puedes editar **Año** y **Periodo** aquí.")
    
    df_proy = load_data("Proyectos")
    df_ent = load_data("Entregables")

    if not df_proy.empty and "Año" in df_proy.columns:
        if "Categoría" in df_proy.columns: df_proy["Categoría"] = df_proy["Categoría"].apply(limpiar_textos)
        if not df_ent.empty and "Subcategoría" in df_ent.columns: df_ent["Subcategoría"] = df_ent["Subcategoría"].apply(limpiar_textos)

        todas_cats = set(); todas_subs = set()
        for c in df_proy["Categoría"].dropna(): todas_cats.update([limpiar_textos(x) for x in str(c).split(',')])
        if not df_ent.empty: 
            for s in df_ent["Subcategoría"].dropna(): todas_subs.update([limpiar_textos(x) for x in str(s).split(',')])

        c0, c1, c2, c3, c4 = st.columns(5)
        f_nom = c0.multiselect("🔍 Proyecto:", sorted(df_proy["Nombre del Proyecto"].unique()))
        f_ano = c1.multiselect("Año:", sorted(df_proy["Año"].unique()))
        f_per = c2.multiselect("Periodo:", ["Primavera", "Verano", "Otoño"])
        f_cat = c3.multiselect("Categoría:", sorted(list(todas_cats)))
        f_sub = c4.multiselect("Subcategoría:", sorted(list(todas_subs)))

        df_v = df_proy.copy()
        df_ev = df_ent.copy() if not df_ent.empty else pd.DataFrame()

        if f_nom: df_v = df_v[df_v["Nombre del Proyecto"].isin(f_nom)]
        if f_ano: df_v = df_v[df_v["Año"].isin(f_ano)]
        if f_per: df_v = df_v[df_v["Periodo"].isin(f_per)]
        if f_cat: df_v = df_v[df_v["Categoría"].apply(lambda x: any(limpiar_textos(c) in f_cat for c in str(x).split(',')))]
        if f_sub and not df_ev.empty:
            df_ev = df_ev[df_ev["Subcategoría"].apply(lambda x: any(limpiar_textos(s) in f_sub for s in str(x).split(',')))]
            df_v = df_v[df_v["Nombre del Proyecto"].isin(df_ev["Proyecto_Padre"].unique())]

        st.markdown("---")

        with st.expander(f"📂 1. Tabla de Proyectos ({len(df_v)})", expanded=True):
            ed_p = st.data_editor(
                df_v, 
                use_container_width=True, 
                key="ep", 
                num_rows="fixed", 
                column_config={
                    "Categoría": st.column_config.TextColumn("Categoría(s)"),
                    "Año": st.column_config.NumberColumn("Año", format="%d", step=1, required=True),
                    "Periodo": st.column_config.SelectboxColumn("Periodo", options=["Primavera", "Verano", "Otoño"], required=True)
                }
            )
            if st.button("💾 Actualizar y Corregir Proyectos"):
                if "Categoría" in ed_p.columns: ed_p["Categoría"] = ed_p["Categoría"].apply(limpiar_textos)
                df_master_proy = load_data("Proyectos")
                df_master_proy.update(ed_p) 
                save_data(df_master_proy, "Proyectos")
                st.success("✅ Guardado. Año, Periodo y datos actualizados.")

        with st.expander("📦 2. Tabla de Entregables Asociados", expanded=True):
            if not df_ent.empty:
                if f_sub: df_ef = df_ev[df_ev["Proyecto_Padre"].isin(df_v["Nombre del Proyecto"].unique())]
                else: df_ef = df_ent[df_ent["Proyecto_Padre"].isin(df_v["Nombre del Proyecto"].unique())]
                
                if not df_ef.empty:
                    ed_e = st.data_editor(df_ef, use_container_width=True, key="ee", num_rows="fixed", column_config={"Subcategoría": st.column_config.TextColumn("Subcategoría")})
                    if st.button("💾 Actualizar y Corregir Entregables"):
                        if "Subcategoría" in ed_e.columns: ed_e["Subcategoría"] = ed_e["Subcategoría"].apply(limpiar_textos)
                        df_master_ent = load_data("Entregables")
                        df_master_ent.update(ed_e)
                        save_data(df_master_ent, "Entregables")
                        st.success("✅ Guardado.")
                else: st.info("No hay entregables para esta selección.")
            else: st.info("Base de datos vacía.")

        with st.expander("🗑️ Zona de Borrado (Peligro)", expanded=False):
            ops = df_v["Nombre del Proyecto"].unique()
            if len(ops) > 0:
                d = st.selectbox("Eliminar:", ops)
                if st.button("Eliminar Definitivamente"):
                    save_data(df_proy[df_proy["Nombre del Proyecto"]!=d], "Proyectos")
                    if not df_ent.empty: save_data(df_ent[df_ent["Proyecto_Padre"]!=d], "Entregables")
                    st.success("Eliminado"); time.sleep(1); st.rerun()
    else: st.info("Cargando...")

# ==========================================
# PESTAÑA 4
# ==========================================
with tab4:
    st.header("📊 Estadísticas en Vivo")
    try: df_p_s = load_data("Proyectos"); df_e_s = load_data("Entregables")
    except: df_p_s = pd.DataFrame(); df_e_s = pd.DataFrame()

    if not df_p_s.empty and "Año" in df_p_s.columns:
        if "Categoría" in df_p_s.columns: df_p_s["Categoría"] = df_p_s["Categoría"].apply(limpiar_textos)
        if not df_e_s.empty: df_e_s["Subcategoría"] = df_e_s["Subcategoría"].apply(limpiar_textos)

        cats_g = set(); subs_g = set()
        for c in df_p_s["Categoría"].dropna(): cats_g.update([x.strip() for x in str(c).split(',') if x.strip()])
        if not df_e_s.empty: 
            for s in df_e_s["Subcategoría"].dropna(): subs_g.update([x.strip() for x in str(s).split(',') if x.strip()])

        c1, c2, c3, c4 = st.columns(4)
        yg = c1.multiselect("Año", sorted(df_p_s["Año"].unique()), default=sorted(df_p_s["Año"].unique()))
        pg = c2.multiselect("Periodo", ["Primavera", "Verano", "Otoño"], default=["Primavera", "Verano", "Otoño"])
        cg = c3.multiselect("Categoría", sorted(list(cats_g)))
        sg = c4.multiselect("Subcategoría", sorted(list(subs_g)))

        df_f = df_p_s[df_p_s["Año"].isin(yg) & df_p_s["Periodo"].isin(pg)]
        df_e_f = df_e_s.copy() if not df_e_s.empty else pd.DataFrame()

        if cg: df_f = df_f[df_f["Categoría"].apply(lambda x: any(item in cg for item in str(x).split(', ')))]
        if sg and not df_e_f.empty:
            df_e_f = df_e_f[df_e_f["Subcategoría"].apply(lambda x: any(item in sg for item in str(x).split(', ')))]
            df_f = df_f[df_f["Nombre del Proyecto"].isin(df_e_f["Proyecto_Padre"].unique())]

        if df_f.empty: st.warning("Sin datos.")
        else:
            st.markdown("---")
            if df_f["Año"].nunique() > 1:
                st.subheader("📅 Evolución Anual")
                pa = df_f["Año"].value_counts().reset_index(); pa.columns=["Año","Total"]; pa["Tipo"]="Proyectos"
                vis = df_f["Nombre del Proyecto"].unique()
                if not df_e_s.empty:
                    ev = df_e_f[df_e_f["Proyecto_Padre"].isin(vis)] if sg else df_e_s[df_e_s["Proyecto_Padre"].isin(vis)]
                    mapa = df_f.set_index("Nombre del Proyecto")["Año"].to_dict()
                    ev["Año_R"] = ev["Proyecto_Padre"].map(mapa); ev = ev.dropna(subset=["Año_R"])
                    ea = ev["Año_R"].value_counts().reset_index(); ea.columns=["Año","Total"]; ea["Tipo"]="Entregables"
                else: ea = pd.DataFrame()
                
                df_chart = pd.concat([pa, ea])
                base = alt.Chart(df_chart).encode(
                    x=alt.X('Tipo:N', axis=None),
                    color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Proyectos', 'Entregables'], range=['#FFFFFF', '#FFD700']), legend=alt.Legend(title="Tipo", labelColor="white", titleColor="white"))
                )
                bars = base.mark_bar(size=30, cornerRadius=5).encode(y='Total:Q')
                text = base.mark_text(dy=-10, color='white').encode(y='Total:Q', text=alt.Text('Total:Q'))
                chart = alt.layer(bars, text).properties(width=100, height=250).facet(column=alt.Column('Año:O', header=alt.Header(labelColor="white", titleColor="white"))).configure_view(stroke='transparent')
                st.altair_chart(chart)
            else: st.info("Registra más años para ver la evolución.")

            st.markdown("---")
            k1, k2 = st.columns(2)
            k1.metric("Proyectos", len(df_f))
            vis = df_f["Nombre del Proyecto"].unique()
            ev_final = (df_e_f if sg else df_e_s)[(df_e_f if sg else df_e_s)["Proyecto_Padre"].isin(vis)] if not df_e_s.empty else pd.DataFrame()
            k2.metric("Entregables", len(ev_final))

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Por Periodo")
                data_p = df_f["Periodo"].value_counts().reset_index(); data_p.columns=["Periodo", "Total"]
                graficar_oscuro(data_p, "Periodo", "Total", "Periodo", "Total", "#FFFFFF")
            with c2:
                st.subheader("Por Categoría")
                sc = df_f["Categoría"].str.split(',').explode().str.strip(); sc=sc[sc!=""]; sc=sc[sc!="Nan"]
                data_c = sc.value_counts().reset_index(); data_c.columns=["Categoría", "Total"]
                graficar_oscuro(data_c, "Categoría", "Total", "Categoría", "Total", "#E0E0E0")
            
            st.markdown("---")
            st.subheader("📦 Subcategorías")
            if not ev_final.empty:
                ss = ev_final["Subcategoría"].str.split(',').explode().str.strip(); ss=ss[ss!=""]; ss=ss[ss!="Nan"]
                data_s = ss.value_counts().reset_index(); data_s.columns=["Subcategoría", "Total"]
                graficar_oscuro(data_s, "Subcategoría", "Total", "Subcategoría", "Total", "#CCCCCC")

# ==========================================
# PESTAÑA 5
# ==========================================
with tab5:
    st.header("📥 Exportar")
    if st.button("Generar Excel"):
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine='openpyxl') as w: load_data("Proyectos").to_excel(w, 'Proyectos', index=False); load_data("Entregables").to_excel(w, 'Entregables', index=False)
        st.download_button("⬇️ Descargar", b.getvalue(), "Reporte.xlsx")

# ==========================================
# PESTAÑA 6: GLOSARIO
# ==========================================
with tab6:
    st.header("📖 Glosario de Términos")
    st.markdown("""
    ### 🗂️ Categorías

    * **Gestión:** Archivos que tengan que ver con la Dirección integral del proyecto (artística, técnica y administrativa), proyectos y subproyectos de la organización, así como la asignación de recursos (presupuestos, cotizaciones, inventarios, análisis de recursos humanos), ejecución y control del proyecto, como rutas críticas, cronogramas, etc.
    * **Comunicación:** Diseño y ejecución de mensajes, canales  para alinear a internos/externos. Plan de comunicación, gestión de interesados, branding interno y externo, documentos de gestión de redes sociales, página web, marketing, memoria/archivo.
    * **Infraestructura:** Instalaciones fijas y móviles, planos arquitectónicos, señalética. Mobiliario y equipo técnico (tramoya, producción, herramientas, tecnológico). Mantenimiento de instalaciones.
    * **Investigación:** História de la finca, del CEDRAM, mapeos de la zona, sobre Pátzcuaro, sobre públicos, FODA, Círculos de Rosso, reporte PAP, presentación final PAP etc.

    ---

    ### 📂 Subcategorías

    #### 🔹 GESTIÓN
    * **Administración:** Todo lo relacionado con cronogramas, planteamiento de necesidades, planificación, seguimiento y toma de decisiones.
    * **Financiamiento:** Archivos de seguimiento a las becas, guías para aplicación a distintos planes de financiamiento, presupuestos, cotizaciones, otros recursos con información de posibles donantes, patrocinios, etc.
    * **Vinculación:** Información de contacto, investigación y formatos de comunicación para y de proyectos que te acerquen a determinados públicos y agentes externos: personas, líderes de opinión, escuelas, planteles educativos con los que el CEDRAM puede generar un lazo. Relaciones públicas. Con quién le convendría al CEDRAM trabajar de cerca y cómo puede acercarse.

    #### 🔹 COMUNICACIÓN
    * **Memoria/archivo CEDRAM:** Archivos como fotografías, videos, etc. que funcionen como memoria de las actividades realizadas por el equipo del CEDRAM.
    * **Memoria/archivo PAP:** Archivos como fotografías, videos, etc. que funcionen como memoria de las actividades realizadas por el equipo del PAP.
    * **Diseño:** Todo lo relacionado con la creación visual y conceptual de los proyectos como por ejemplo ideas gráficas, referencias, propuestas creativas, identidad visual, materiales de apoyo según el proyecto (folletos, pósters, infografías, plantillas).
    * **Difusión:** Estrategias y materiales para dar a conocer los proyectos. Incluye contenido para redes sociales, campañas de comunicación, textos, imágenes, videos, calendarios de publicación y seguimiento de alcance e impacto, souvenirs.

    #### 🔹 INFRAESTRUCTURA
    * **Diseño arquitectónico:** Archivos relacionados con el planteamiento y desarrollo de espacios. Incluye planos, conceptos espaciales, renders, referencias arquitectónicas, propuestas de uso de espacios y evolución de diseño.
    * **Mantenimiento:** Señalética, mantenimiento y remodelación de espacios.
    * **Productos teatrales:** Vestuario (diseño y realización), Kamishibai.
    """)
