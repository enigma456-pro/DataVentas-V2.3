"""
DATAVENTAS - BACKEND
Servidor que conecta con Belvo para obtener transacciones bancarias
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
from collections import Counter
import os

app = Flask(__name__)
CORS(app)  # Permite que el frontend se comunique con el backend

# ============================================================
# CONFIGURACIÓN - ¡CAMBIAR CON TUS DATOS REALES DE BELVO!
# ============================================================

# Obtén estas credenciales desde tu panel de Belvo
BELVO_SECRET_ID = "TU_SECRET_ID_AQUI"        # <--- CAMBIAR
BELVO_SECRET_PASSWORD = "TU_SECRET_PASSWORD"  # <--- CAMBIAR
BELVO_ENVIRONMENT = "sandbox"  # "sandbox" para pruebas, "production" para producción

# ============================================================
# ENDPOINT 1: Generar token para el widget de Belvo
# ============================================================

@app.route('/api/token', methods=['GET'])
def generar_token():
    """
    Genera un token temporal (válido por 10 minutos) 
    para que el widget de Belvo pueda funcionar.
    """
    try:
        url = f"https://{BELVO_ENVIRONMENT}.belvo.com/api/token/"
        
        payload = {
            "id": BELVO_SECRET_ID,
            "password": BELVO_SECRET_PASSWORD,
            "scopes": "read_institutions,write_links,read_links,read_balances,read_transactions"
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return jsonify({
            "success": True,
            "access_token": data.get("access_token")
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================
# ENDPOINT 2: Obtener transacciones del banco
# ============================================================

@app.route('/api/transacciones', methods=['POST'])
def obtener_transacciones():
    """
    Recibe el link_id del widget y obtiene las transacciones reales del banco.
    """
    try:
        data = request.json
        link_id = data.get('link_id')
        
        if not link_id:
            return jsonify({"success": False, "error": "Falta link_id"}), 400
        
        # Fechas del mes actual
        hoy = datetime.now().date()
        primer_dia_mes = hoy.replace(day=1)
        
        # URL de la API de Belvo para transacciones
        url = f"https://{BELVO_ENVIRONMENT}.belvo.com/api/transactions/"
        
        payload = {
            "link": link_id,
            "date_from": primer_dia_mes.isoformat(),
            "date_to": hoy.isoformat()
        }
        
        # Autenticación básica con las credenciales de Belvo
        response = requests.post(
            url, 
            json=payload, 
            auth=(BELVO_SECRET_ID, BELVO_SECRET_PASSWORD)
        )
        response.raise_for_status()
        
        transacciones = response.json()
        
        # Procesar los datos
        resultados = procesar_transacciones(transacciones)
        
        return jsonify({
            "success": True,
            "datos": resultados
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================
# FUNCIÓN: Procesar transacciones
# ============================================================

def procesar_transacciones(transacciones):
    """
    Extrae descripciones y montos de las transacciones,
    y genera estadísticas de ventas.
    """
    resultados = transacciones.get('results', [])
    
    # Filtrar solo ingresos (monto > 0)
    ingresos = [t for t in resultados if t.get('amount', 0) > 0]
    
    ventas = []
    for ingreso in ingresos:
        descripcion = ingreso.get('description', 'Sin descripción')
        monto = abs(ingreso.get('amount', 0))
        fecha = ingreso.get('created_at', datetime.now())
        
        ventas.append({
            'descripcion': descripcion,
            'monto': monto,
            'fecha': fecha
        })
    
    # Contar por descripción
    contador = Counter([v['descripcion'] for v in ventas])
    
    # Resumen de ventas
    resumen_ventas = []
    for desc, count in contador.items():
        ingreso_total = sum(v['monto'] for v in ventas if v['descripcion'] == desc)
        resumen_ventas.append({
            "producto": desc,
            "unidades": count,
            "ingreso_total": round(ingreso_total, 2)
        })
    
    resumen_ventas.sort(key=lambda x: x['unidades'], reverse=True)
    
    # Detalle de ventas
    detalle_ventas = []
    for v in ventas:
        detalle_ventas.append({
            "fecha": v['fecha'],
            "descripcion": v['descripcion'],
            "monto": round(v['monto'], 2)
        })
    
    return {
        "total_ingresos": round(sum(v['monto'] for v in ventas), 2),
        "total_ventas": sum(contador.values()),
        "total_productos": len(resumen_ventas),
        "resumen_ventas": resumen_ventas[:10],  # Top 10
        "detalle_ventas": detalle_ventas
    }

# ============================================================
# ENDPOINT 3: Verificar estado del servidor
# ============================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica que el servidor esté funcionando."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })

# ============================================================
# INICIAR EL SERVIDOR
# ============================================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 DATAVENTAS - BACKEND")
    print("=" * 50)
    print(f"📍 Puerto: 5000")
    print(f"🔗 http://localhost:5000")
    print(f"🌐 Entorno: {BELVO_ENVIRONMENT}")
    print("=" * 50)
    print("Presiona CTRL+C para detener el servidor")
    print("=" * 50)
    app.run(debug=True, port=5000, host='0.0.0.0')
