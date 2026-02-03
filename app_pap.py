import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión PAP - Nube", layout="wide", page_icon="☁️")

# --- LISTAS FIJAS ---
CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]
SUBCATEGORIAS_FIJAS = [
    "Financiamiento", "Vinculación", "Memoria/archivo CEDRAM", 
    "Memoria/archivo PAP", "Diseño", "Difusión", 
    "Diseño arquitectónico", "Mantenimiento", "Productos teatrales"
]

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN LOAD_DATA BLINDADA (A prueba de errores) ---
def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            # Elimina espacios invisibles en los encabezados
            df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)

# --- TÍTULO ---
st.title("☁️ Sistema PAP: Colaborativo")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Registrar PROYECTO", 
    "2. Registrar ENTREGABLES", 
    "3. 🔍 Buscar / Eliminar",
    "4. 📊 Gráficas",
    "5. 📥 Descargar Excel"
])

# ==========================================
# PESTAÑA 1: REGISTRO DE PROYECTOS
# ==========================================
with tab1:
    st.subheader("Nuevo Proyecto")
    with st.form("form_proyecto", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            anio = st.number_input("Año", min_value=2019, max_value=2030, value=datetime.now().year)
        with col2:
            periodo = st.selectbox("Periodo", ["Primavera", "Verano", "Otoño"])
        with col3:
            categoria_proy = st.selectbox("Categoría General", CATEGORIAS_LISTA)

        nombre_proyecto = st.text_input("Nombre del Proyecto")
        descripcion = st.text_area("Descripción")
        
        c_ent, c_com = st.columns(2)
        with c_ent:
            num_entregables = st.number_input("Estimado de Entregables", min_value=0, step=1)
        with c_com:
            comentarios = st.text_area("Comentarios")

        if st.form_submit_button("💾 Guardar en Nube"):
            if not nombre_proyecto:
                st.error("El nombre es obligatorio")
            else:
                df_proy = load_data("Proyectos")
                
                # Checar duplicados
                if not df_proy.empty and "Nombre del Proyecto" in df_proy.columns and nombre_proyecto in df_proy["Nombre del Proyecto"].values:
                     st.warning("⚠️ Ya existe un proyecto con ese nombre.")

                nuevo = {
                    "Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre_proyecto,
                    "Descripción": descripcion, "Num_Entregables": num_entregables,
                    "Categoría": categoria_proy, "Comentarios": comentarios,
                    "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                df_updated = pd.concat([df_proy, pd.DataFrame([nuevo])], ignore_index=True)
                save_data(df_updated, "Proyectos")
                st.success("¡Proyecto guardado!")

# ==========================================
# PESTAÑA 2: REGISTRO DE ENTREGABLES
# ==========================================
with tab2:
    st.subheader("Agregar Entregables")
    df_p = load_data("Proyectos")
    
    if df_p.empty:
        st.warning("No hay proyectos registrados en la nube.")
    else:
        # Aseguramos que exista la columna antes de ordenar
        if "Nombre del Proyecto" in df_p.columns:
            lista_proyectos = sorted(df_p["Nombre del Proyecto"].unique().tolist())
            proyecto_sel = st.selectbox("Selecciona el Proyecto:", lista_proyectos)
            
            # Detectar categoría automática
            cat_auto = "Desconocida"
            if "Categoría" in df_p.columns:
                valores = df_p[df_p["Nombre del Proyecto"] == proyecto_sel]["Categoría"].values
                if len(valores) > 0:
                    cat_auto = valores[0]
            
            st.info(f"Categoría detectada: **{cat_auto}**")

            st.markdown("---")
            with st.form("form_entregable", clear_on_submit=True):
                entregable = st.text_input("Nombre del Entregable")
                contenido = st.text_area("Contenido")
                subcat_ent = st.multiselect("Subcategoría(s)", SUBCATEGORIAS_FIJAS)
                plantillas = st.text_input("Plantillas")
                
                if st.form_submit_button("📥 Agregar a Nube"):
                    df_ent = load_data("Entregables")

                    subcat_str = ", ".join(subcat_ent)
                    nuevo_ent = {
                        "Proyecto_Padre": proyecto_sel, 
                        "Entregable": entregable,
                        "Contenido": contenido, 
                        "Categoría": cat_auto,
                        "Subcategoría": subcat_str, 
                        "Plantillas": plantillas,
                        "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    df_updated_ent = pd.concat([df_ent, pd.DataFrame([nuevo_ent])], ignore_index=True)
                    save_data(df_updated_ent, "Entregables")
                    st.success("Entregable guardado.")
        else:
            st.error("Error en la Base de Datos: No se encuentra la columna 'Nombre del Proyecto'.")

# ==========================================
# PESTAÑA 3: BUSCAR / ELIMINAR
# ==========================================
with tab3:
    st.header("Base de Datos en Vivo")
    df_proy = load_data("Proyectos")
    df_ent = load_data("Entregables")

    if not df_proy.empty and "Año" in df_proy.columns:
        c1, c2 = st.columns(2)
        with c1:
            years = sorted(df_proy["Año"].unique())
            f_year = st.multiselect("Año:", years)
        with c2:
            f_period = st.multiselect("Periodo:", ["Primavera", "Verano", "Otoño"])

        df_view = df_proy.copy()
        if f_year: df_view = df_view[df_view["Año"].isin(f_year)]
        if f_period: df_view = df_view[df_view["Periodo"].isin(f_period)]

        st.dataframe(df_view, use_container_width=True)
        
        st.markdown("### Entregables")
        if not df_ent.empty and "Proyecto_Padre" in df_ent.columns:
            visible_projects = df_view["Nombre del Proyecto"].unique()
            df_ent_view = df_ent[df_ent["Proyecto_Padre"].isin(visible_projects)]
            st.dataframe(df_ent_view, use_container_width=True)
        else:
            st.info("No hay entregables aún.")

        st.markdown("---")
        with st.expander("🗑️ Zona de Borrado (Afecta a Google Sheets)"):
            to_del = st.selectbox("Proyecto a eliminar:", df_proy["Nombre del Proyecto"].unique())
            if st.button("Eliminar Definitivamente"):
                df_proy_new = df_proy[df_proy["Nombre del Proyecto"] != to_del]
                if not df_ent.empty and "Proyecto_Padre" in df_ent.columns:
                    df_ent_new = df_ent[df_ent["Proyecto_Padre"] != to_del]
                    save_data(df_ent_new, "Entregables")
                
                save_data(df_proy_new, "Proyectos")
                st.success("Eliminado de la nube.")
                st.rerun()
    else:
        st.info("Sin datos o error de columnas.")

# ==========================================
# PESTAÑA 4: GRÁFICAS (CORREGIDA)
# ==========================================
with tab4:
    st.header("📊 Estadísticas en Vivo")
    try:
        df_p_s = load_data("Proyectos")
        df_e_s = load_data("Entregables")
    except:
        st.error("No se pudieron cargar los datos.")
        df_p_s = pd.DataFrame()
        df_e_s = pd.DataFrame()

    if not df_p_s.empty and "Año" in df_p_s.columns:
        st.markdown("#### Configuración de Vista")
        col_g1, col_g2 = st.columns(2)
        
        # 1. Filtro Año
        with col_g1:
             years_g = st.multiselect("Filtrar por Año", sorted(df_p_s["Año"].unique()), default=sorted(df_p_s["Año"].unique()))
        
        # 2. Filtro Periodo (AGREGADO)
        with col_g2:
             all_periods = ["Primavera", "Verano", "Otoño"]
             periods_g = st.multiselect("Filtrar por Periodo", all_periods, default=all_periods)
        
        # Aplicamos ambos filtros
        df_filtered = df_p_s[
            df_p_s["Año"].isin(years_g) & 
            df_p_s["Periodo"].isin(periods_g)
        ]
        
        if df_filtered.empty:
            st.warning("No hay datos que coincidan con esos filtros.")
        else:
            st.markdown("---")
            
            # KPIs
            col_kpi1, col_kpi2 = st.columns(2)
            col_kpi1.metric("Proyectos Encontrados", len(df_filtered))
            
            # Para contar entregables, filtramos los entregables que pertenecen a los proyectos filtrados
            proyectos_visibles = df_filtered["Nombre del Proyecto"].unique()
            if not df_e_s.empty and "Proyecto_Padre" in df_e_s.columns:
                df_e_filtered = df_e_s[df_e_s["Proyecto_Padre"].isin(proyectos_visibles)]
                col_kpi2.metric("Entregables Totales", len(df_e_filtered))
            else:
                df_e_filtered = pd.DataFrame()
                col_kpi2.metric("Entregables Totales", 0)

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Proyectos por Periodo")
                st.bar_chart(df_filtered["Periodo"].value_counts())
            with col2:
                st.subheader("Proyectos por Categoría")
                st.bar_chart(df_filtered["Categoría"].value_counts())
                
            st.markdown("---")
            st.subheader("📦 Subcategorías (Filtrado por fecha)")
            if not df_e_filtered.empty and "Subcategoría" in df_e_filtered.columns:
                 # Separa las subcategorías múltiples y las cuenta
                 series_sub = df_e_filtered["Subcategoría"].astype(str).str.split(', ').explode()
                 st.bar_chart(series_sub.value_counts())
            else:
                 st.info("No hay entregables en este periodo para graficar.")

# ==========================================
# PESTAÑA 5: DESCARGAR EXCEL
# ==========================================
with tab5:
    st.header("📥 Exportar Base de Datos")
    st.write("Descarga un respaldo completo.")
    
    if st.button("🔄 Generar Archivo Excel"):
        with st.spinner("Descargando..."):
            try:
                df_proy_down = load_data("Proyectos")
                df_ent_down = load_data("Entregables")
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_proy_down.to_excel(writer, sheet_name='Proyectos', index=False)
                    df_ent_down.to_excel(writer, sheet_name='Entregables', index=False)
                
                st.download_button(
                    label="⬇️ Descargar Excel Listo (.xlsx)",
                    data=buffer.getvalue(),
                    file_name=f"Reporte_PAP_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}")
