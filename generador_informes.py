import pandas as pd
import numpy as np
import json

# ==========================================
# 1. INSTRUCCIONES PARA GOOGLE COLAB
# ==========================================
# 1. Abre Google Colab (colab.research.google.com)
# 2. Sube tus 3 archivos CSV en el panel de la izquierda (icono de carpeta).
# 3. Pega todo este código en una celda y ejecútalo.

def cargar_y_limpiar_datos():
    print("Cargando archivos...")
    try:
        # Cargar archivos (ajusta los nombres si es necesario)
        df_109 = pd.read_csv('109.csv')
        df_81 = pd.read_csv('81.csv')
        df_pw = pd.read_csv('parkway.csv')
        
        # Etiquetar sucursales
        df_109['SUCURSAL'] = 'sede109'
        df_81['SUCURSAL'] = 'sede81'
        df_pw['SUCURSAL'] = 'parkway'
        
        # Unir todo
        df = pd.concat([df_109, df_81, df_pw], ignore_index=True)
        
        # Limpieza de datos
        df = df[~df['PRODUCTO'].str.contains('===', na=False)] # Quitar separadores
        df['PRODUCTO'] = df['PRODUCTO'].str.strip().str.title() # Normalizar nombres
        
        # Convertir a números
        df['PrecioConImpuesto'] = pd.to_numeric(df['PrecioConImpuesto'], errors='coerce').fillna(0)
        df['CANTIDAD'] = pd.to_numeric(df['CANTIDAD'], errors='coerce').fillna(1)
        df['COMENSALES'] = pd.to_numeric(df['COMENSALES'], errors='coerce').fillna(1)
        
        # Calcular Venta Total por línea
        df['Venta_Total_Linea'] = df['CANTIDAD'] * df['PrecioConImpuesto']
        
        print("Datos cargados y limpiados correctamente.\n")
        return df
    except Exception as e:
        print(f"Error cargando los datos. Verifica que los archivos estén subidos a Colab.\nDetalle: {e}")
        return None

def analizar_sucursal(df_filtrado):
    # --- 1. KPIs ---
    # Para ticket y comensales, agrupamos por ORDEN
    ordenes = df_filtrado.groupby('ORDEN').agg({
        'Venta_Total_Linea': 'sum',
        'COMENSALES': 'max' # Tomamos el max de comensales registrado en esa orden
    })
    
    total_ordenes = len(ordenes)
    ticket_promedio = ordenes['Venta_Total_Linea'].mean() if total_ordenes > 0 else 0
    comensales_promedio = ordenes['COMENSALES'].mean() if total_ordenes > 0 else 0
    
    # Formateo de KPIs
    kpi = {
        "orders": f"{total_ordenes:,.0f}",
        "ticket": f"${ticket_promedio:,.0f}",
        "diners": f"{comensales_promedio:.1f}"
    }
    
    # --- 2. PARETO (Por Monto de Ventas) ---
    ventas_prod = df_filtrado.groupby('PRODUCTO')['Venta_Total_Linea'].sum().sort_values(ascending=False)
    # Tomamos el Top 6-8 para la gráfica
    top_pareto = ventas_prod.head(6)
    pareto = {
        "labels": top_pareto.index.tolist(),
        "data": top_pareto.values.tolist()
    }
    
    # --- 3. ANCLAS (Por Cantidad Vendida) ---
    cantidades_prod = df_filtrado.groupby('PRODUCTO')['CANTIDAD'].sum().sort_values(ascending=False)
    top_anclas = cantidades_prod.head(3)
    
    anclas = []
    iconos = ['fa-star', 'fa-fire', 'fa-bolt'] # Iconos genéricos por defecto
    for i, (prod, cant) in enumerate(top_anclas.items()):
        anclas.append({
            "name": prod,
            "icon": iconos[i],
            "qty": f"{cant:,.0f} und",
            "mix": "Producto de alta tracción"
        })
        
    # --- 4. PORTAFOLIO (Categorías A, B, C) ---
    total_prods = len(ventas_prod)
    if total_prods == 0:
        portafolio = {"catA": [], "catB": [], "catC": []}
    else:
        # A: Top 20%
        # B: Siguiente 30%
        # C: Peores 50%
        lim_a = int(total_prods * 0.20)
        lim_b = int(total_prods * 0.50)
        
        cat_A = ventas_prod.iloc[:lim_a].index.tolist()[:5] # Máximo 5 para visualización
        cat_B = ventas_prod.iloc[lim_a:lim_b].index.tolist()[:5]
        cat_C_raw = ventas_prod.iloc[lim_b:].tail(5).index.tolist() # Tomamos los 5 peores reales
        
        cat_C = [
            {"name": prod, "reason": "Baja rotación o nula contribución a ingresos totales."} 
            for prod in cat_C_raw
        ]
        
        portafolio = {
            "catA": cat_A,
            "catB": cat_B,
            "catC": cat_C
        }
        
    return {
        "kpi": kpi,
        "pareto": pareto,
        "anclas": anclas,
        "portafolio": portafolio
    }

def generar_datastore():
    df = cargar_y_limpiar_datos()
    if df is None: return
    
    data_store = {}
    
    # Analizar Total Organización
    data_store['total'] = analizar_sucursal(df)
    
    # Analizar Sucursales Individuales
    for sucursal in ['sede109', 'sede81', 'parkway']:
        df_sucursal = df[df['SUCURSAL'] == sucursal]
        data_store[sucursal] = analizar_sucursal(df_sucursal)
        
    # Generar el código JS a imprimir
    js_output = "const dataStore = " + json.dumps(data_store, indent=4, ensure_ascii=False) + ";"
    
    print("="*60)
    print("¡ÉXITO! COPIA EL SIGUIENTE BLOQUE Y PÉGALO EN TU ARCHIVO HTML")
    print("(Reemplaza el 'const dataStore = {...}' que ya tienes)")
    print("="*60)
    print(js_output)
    print("="*60)

# Ejecutar el proceso
generar_datastore()