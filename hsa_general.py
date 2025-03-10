import streamlit as st
import pandas as pd
from datetime import datetime
import re
import uuid

# Limpiar completamente el caché al inicio
st.cache_data.clear()

# Configuración de la página
st.set_page_config(
    page_title="Alertas de Caducidad HSA",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Generar ID único para esta sesión
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

def format_date(date_str):
    """
    Formatea una fecha en el formato deseado (dd/mm/aa).
    Elimina la parte de tiempo si existe.
    """
    if date_str == 'No disponible':
        return date_str
        
        
    try:
        # Intentar varios formatos de fecha posibles
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y']:
            try:
                date_obj = datetime.strptime(str(date_str), fmt)
                # Retornar en formato dd/mm/yyyy
                return date_obj.strftime('%d/%m/%Y')
            except ValueError:
                continue
                
        # Si no se pudo convertir con ninguno de los formatos, devolver el original
        return date_str
    except:
        # En caso de cualquier error, devolver el original
        return date_str

def calcular_caducidad(row):
    """
    Evalúa la caducidad del expediente comparando la fecha actual con la fecha de caducidad.
    Se actualiza automáticamente cada día sin necesidad de modificar el código.
    """
    # Caso especial para expedientes con tema REVOCATORIA DE MANDATO
    if 'TEMA' in row and row['TEMA'] == 'REVOCATORIA DE MANDATO':
        return {
            'fecha': 'NO APLICA', 
            'mensaje': 'NO APLICA',
            'estilo': "color: #7f8c8d; font-weight: bold;",
            'dias_restantes': 999  # Un valor alto para que siempre sea considerado como vigente
        }
    
    # Obtener la fecha actual
    fecha_actual = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Comprobar si tenemos la columna de fecha de caducidad
    fecha_caducidad = None
    
    # Verificar diferentes posibles nombres de columna
    for col_name in ['FECHA DE CADUCIDAD', 'FECHA DE CADUCIDAD ', 'CADUCIDAD', 'FECHA CADUCIDAD']:
        if col_name in row and pd.notna(row[col_name]):
            fecha_caducidad = row[col_name]
            break
    
    # Si no hay fecha de caducidad disponible
    if fecha_caducidad is None or fecha_caducidad == 'No disponible':
        return "No disponible"
    
    try:
        # Asegurar que fecha_caducidad es un objeto datetime
        if isinstance(fecha_caducidad, pd.Timestamp) or isinstance(fecha_caducidad, datetime):
            # Ya es un objeto datetime/timestamp, asegurar que no tiene componente de hora
            fecha_caducidad = fecha_caducidad.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Si es una cadena, intentar convertirla 
            try:
                fecha_caducidad = pd.to_datetime(fecha_caducidad)
                fecha_caducidad = fecha_caducidad.replace(hour=0, minute=0, second=0, microsecond=0)
            except:
                return "No disponible"
        
        # Calcular los días restantes entre hoy y la fecha de caducidad
        dias_restantes = (fecha_caducidad - fecha_actual).days
        
        # Formatear fecha de caducidad para mostrar
        fecha_caducidad_str = fecha_caducidad.strftime('%d/%m/%Y')
        
        # Determinar estado y mensaje según los días restantes
        if dias_restantes < 0:
            mensaje = f"¡CADUCADO HACE {abs(dias_restantes)} DÍAS!"
            estilo = "color: #e74c3c; font-weight: bold;"
        elif dias_restantes == 0:
            mensaje = "¡CADUCA HOY!"
            estilo = "color: #e67e22; font-weight: bold;"
        elif dias_restantes <= 30:
            mensaje = f"¡FALTAN {dias_restantes} DÍAS PARA CADUCAR!"
            estilo = "color: #f39c12; font-weight: bold;"
        else:
            mensaje = f"VIGENTE - FALTAN {dias_restantes} DÍAS"
            estilo = "color: #2ecc71; font-weight: bold;"
        
        return {
            'fecha': fecha_caducidad_str, 
            'mensaje': mensaje,
            'estilo': estilo,
            'dias_restantes': dias_restantes
        }
    except Exception as e:
        return "No disponible"

def render_caducidad(caducidad_info):
    """
    Renderiza la información de caducidad en HTML.
    """
    if not isinstance(caducidad_info, dict):
        return f"<div>{caducidad_info}</div>"
    
    # Caso especial para NO APLICA
    if caducidad_info.get('mensaje') == 'NO APLICA':
        return f"""
        <div>
            <div style="{caducidad_info['estilo']}">NO APLICA</div>
            <div>Fecha límite: NO APLICA</div>
        </div>
        """
    
    # Icono según el estado
    if caducidad_info.get('dias_restantes', 0) < 0:
        icono = "⚠️"  # Caducado
    elif caducidad_info.get('dias_restantes', 0) <= 30:
        icono = "⏳"  # Próximo a caducar
    else:
        icono = "✅"  # Vigente
    
    html = f"""
    <div>
        <div style="{caducidad_info['estilo']}">{icono} {caducidad_info['mensaje']}</div>
        <div>Fecha límite: {caducidad_info['fecha']}</div>
    </div>
    """
    return html

# Ruta al archivo Excel de HSA
EXCEL_PATH = 'PRUEBA HSA.xlsx'  # Ajusta esta ruta según necesites

# Función para cargar datos desde el Excel
def cargar_datos():
    try:
        # Primero intentamos leer el Excel sin parse_dates para detectar los nombres exactos de columnas
        df_check = pd.read_excel(EXCEL_PATH, sheet_name='HSA')
        
        # Verificar qué columnas de fecha existen realmente
        columnas_fecha = []
        for col in df_check.columns:
            if 'FECHA' in col.upper():
                columnas_fecha.append(col)
        
        # Ahora leemos los datos con parse_dates aplicado a las columnas que realmente existen
        df = pd.read_excel(
            EXCEL_PATH, 
            sheet_name='HSA',
            parse_dates=columnas_fecha
        )
        
        # Limpiar nombres de columnas (eliminar espacios extras)
        df.columns = df.columns.str.strip()
        
        # Eliminar duplicados por número de expediente si existieran
        if 'EXPEDIENTE' in df.columns:
            df = df.drop_duplicates(subset=['EXPEDIENTE'])
        
        # Limpiar datos y manejar valores nulos
        df = df.fillna('No disponible')
        
        return df
            
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo Excel: {str(e)}")
        st.info(f"ℹ️ Verifica que el archivo exista en la ruta: {EXCEL_PATH}")
        return pd.DataFrame()

# Estilos CSS personalizados
st.markdown("""
    <style>
        .title-container {
            background-color: #1f77b4;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            color: white;
            text-align: center;
        }
        .data-container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
        .asesor-card {
            background-color: #f0f7ff;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin-bottom: 15px;
            border-left: 5px solid #1f77b4;
        }
        .expediente-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 10px;
            border-top: 3px solid #1f77b4;
            display: grid;
            grid-template-columns: 1fr 1fr 2fr 2fr;
            gap: 10px;
            align-items: center;
        }
        .expediente-header {
            font-weight: bold;
            border-bottom: 1px solid #ddd;
            padding-bottom: 8px;
            margin-bottom: 10px;
            display: grid;
            grid-template-columns: 1fr 1fr 2fr 2fr;
            gap: 10px;
        }
        .caducidad-badge {
            padding: 5px 10px;
            border-radius: 12px;
            font-weight: bold;
            display: inline-block;
            text-align: center;
        }
        .caducado {
            background-color: #ffcccc;
            color: #e74c3c;
        }
        .hoy {
            background-color: #ffe0cc;
            color: #e67e22;
        }
        .proximo {
            background-color: #fff3cc;
            color: #f39c12;
        }
        .vigente {
            background-color: #d4f7e6;
            color: #2ecc71;
        }
        .summary-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .summary-card {
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }
        .summary-caducados {
            border-top: 4px solid #e74c3c;
        }
        .summary-hoy {
            border-top: 4px solid #e67e22;
        }
        .summary-proximos {
            border-top: 4px solid #f39c12;
        }
        .summary-vigentes {
            border-top: 4px solid #2ecc71;
        }
        .summary-number {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
    </style>
""", unsafe_allow_html=True)

# Título principal 
st.markdown("""
    <div class="title-container">
        <h1>⏱️ Alertas de Caducidad HSA</h1>
        <p style='font-size: 18px;'>Sistema de seguimiento de expedientes y fechas límite</p>
    </div>
""", unsafe_allow_html=True)

# Cargar datos
df = cargar_datos()

# Procesar datos para calcular caducidades
df_procesado = df.copy()
df_procesado['info_caducidad'] = df_procesado.apply(calcular_caducidad, axis=1)

# Filtros en la barra lateral
st.sidebar.header("🔍 Filtros")

# Filtro por estado de caducidad
estados_caducidad = ["Todos", "Caducados", "Caducan hoy", "Próximos a caducar (30 días)", "Vigentes", "No Aplica"]
estado_seleccionado = st.sidebar.selectbox(
    "Estado de caducidad:",
    estados_caducidad,
    key=f"estado_caducidad_{st.session_state.session_id}"
)

# Filtro por tema
temas_unicos = ["Todos"] + sorted(df['TEMA'].unique().tolist())
tema_seleccionado = st.sidebar.selectbox(
    "Tema del expediente:",
    temas_unicos,
    key=f"tema_{st.session_state.session_id}"
)

# Filtro por asesor
asesores_unicos = ["Todos"] + sorted(df['ASESOR'].unique().tolist())
asesor_seleccionado = st.sidebar.selectbox(
    "Asesor:",
    asesores_unicos,
    key=f"asesor_{st.session_state.session_id}"
)

# Aplicar filtros
df_filtrado = df_procesado.copy()

# Filtro por estado de caducidad
if estado_seleccionado != "Todos":
    def filtrar_por_estado(row):
        if not isinstance(row['info_caducidad'], dict):
            return False
            
        if estado_seleccionado == "No Aplica" and row['info_caducidad'].get('mensaje') == 'NO APLICA':
            return True
            
        dias_restantes = row['info_caducidad'].get('dias_restantes', 0)
        
        if estado_seleccionado == "Caducados":
            return dias_restantes < 0
        elif estado_seleccionado == "Caducan hoy":
            return dias_restantes == 0
        elif estado_seleccionado == "Próximos a caducar (30 días)":
            return 0 < dias_restantes <= 30
        elif estado_seleccionado == "Vigentes":
            return dias_restantes > 30 and row['info_caducidad'].get('mensaje') != 'NO APLICA'
        return True
        
    df_filtrado = df_filtrado[df_filtrado.apply(filtrar_por_estado, axis=1)]

# Filtro por tema
if tema_seleccionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['TEMA'] == tema_seleccionado]

# Filtro por asesor
if asesor_seleccionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['ASESOR'] == asesor_seleccionado]

# Calcular estadísticas para el resumen
def contar_por_estado(df):
    caducados = 0
    hoy = 0
    proximos = 0
    vigentes = 0
    no_aplica = 0
    
    for _, row in df.iterrows():
        if isinstance(row['info_caducidad'], dict):
            if row['info_caducidad'].get('mensaje') == 'NO APLICA':
                no_aplica += 1
                continue
                
            dias = row['info_caducidad'].get('dias_restantes', 0)
            if dias < 0:
                caducados += 1
            elif dias == 0:
                hoy += 1
            elif dias <= 30:
                proximos += 1
            else:
                vigentes += 1
    
    return {
        'caducados': caducados,
        'hoy': hoy,
        'proximos': proximos,
        'vigentes': vigentes,
        'no_aplica': no_aplica,
        'total': len(df)
    }

estadisticas = contar_por_estado(df_procesado)
estadisticas_filtradas = contar_por_estado(df_filtrado)

# Mostrar resumen de estadísticas
st.markdown("""
    <h3>📊 Resumen de expedientes</h3>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="summary-container">
        <div class="summary-card summary-caducados">
            <h4>⚠️ Caducados</h4>
            <div class="summary-number">{estadisticas_filtradas['caducados']}</div>
            <div>de {estadisticas['caducados']} totales</div>
        </div>
        <div class="summary-card summary-hoy">
            <h4>🚨 Caducan hoy</h4>
            <div class="summary-number">{estadisticas_filtradas['hoy']}</div>
            <div>de {estadisticas['hoy']} totales</div>
        </div>
        <div class="summary-card summary-proximos">
            <h4>⏳ Próximos</h4>
            <div class="summary-number">{estadisticas_filtradas['proximos']}</div>
            <div>de {estadisticas['proximos']} totales</div>
        </div>
        <div class="summary-card summary-vigentes">
            <h4>✅ Vigentes</h4>
            <div class="summary-number">{estadisticas_filtradas['vigentes']}</div>
            <div>de {estadisticas['vigentes']} totales</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Mostrar los No Aplica en una tarjeta adicional
st.markdown(f"""
    <div style="background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                text-align: center; border-top: 4px solid #7f8c8d; margin-bottom: 20px;">
        <h4>🔄 No Aplica (Revocatoria de Mandato)</h4>
        <div style="font-size: 24px; font-weight: bold; margin: 10px 0;">{estadisticas_filtradas['no_aplica']}</div>
        <div>de {estadisticas['no_aplica']} totales</div>
    </div>
""", unsafe_allow_html=True)

# Mensaje si no hay expedientes
if df_filtrado.empty:
    st.warning("⚠️ No se encontraron expedientes con los filtros seleccionados.")
else:
    st.success(f"✅ Se encontraron {len(df_filtrado)} expedientes que coinciden con los filtros.")
    
    # Agrupar por asesor
    asesores_grupos = df_filtrado.groupby('ASESOR')
    
    # Mostrar expedientes agrupados por asesor
    for asesor, grupo in asesores_grupos:
        with st.expander(f"👤 {asesor} ({len(grupo)} expedientes)"):
            # Encabezado de la tabla
            st.markdown("""
                <div class="expediente-header">
                    <div>Expediente</div>
                    <div>Fecha de Reparto</div>
                    <div>Caducidad</div>
                    <div>Tema</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Mostrar expedientes de este asesor
            for _, row in grupo.iterrows():
                # Determinar el estado para la clase CSS
                if row['TEMA'] == 'REVOCATORIA DE MANDATO':
                    estado_clase = "no-aplica"
                else:
                    estado_clase = "vigente"
                    if isinstance(row['info_caducidad'], dict):
                        dias = row['info_caducidad'].get('dias_restantes', 0)
                        if dias < 0:
                            estado_clase = "caducado"
                        elif dias == 0:
                            estado_clase = "hoy"
                        elif dias <= 30:
                            estado_clase = "proximo"
                
                # Extraer fecha de reparto (comprobando diferentes posibles nombres de columna)
                fecha_reparto = None
                for col_name in ['FECHA DE REPARTO', 'FECHA DE REPARTO ', 'REPARTO', 'FECHA REPARTO']:
                    if col_name in row and pd.notna(row[col_name]):
                        fecha_reparto = row[col_name]
                        break
                        
                if isinstance(fecha_reparto, pd.Timestamp):
                    fecha_reparto = fecha_reparto.strftime('%d/%m/%Y')
                elif fecha_reparto is None:
                    fecha_reparto = "No disponible"
                    
                # Crear HTML para el expediente
                st.markdown(f"""
                    <div class="expediente-item">
                        <div><strong>{row['EXPEDIENTE']}</strong></div>
                        <div>{format_date(fecha_reparto)}</div>
                        <div>{render_caducidad(row['info_caducidad'])}</div>
                        <div>{row['TEMA']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
    # Opción para ver todos los expedientes en una tabla
    if st.checkbox("📋 Ver todos los expedientes en formato tabla"):
        # Seleccionar columnas relevantes
        df_tabla = df_filtrado[['ASESOR', 'EXPEDIENTE', 'FECHA DE REPARTO', 'TEMA', 'SEGUIMIENTO']]
        
        # Añadir columna de estado de caducidad
        df_tabla['Estado Caducidad'] = df_filtrado.apply(
            lambda row: row['info_caducidad']['mensaje'] if isinstance(row['info_caducidad'], dict) else "No disponible", 
            axis=1
        )
        
        # Mostrar tabla
        st.dataframe(df_tabla, use_container_width=True)