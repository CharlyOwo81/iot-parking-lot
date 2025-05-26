from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="estacionamiento"
)

@app.route('/collect', methods=['POST'])
def collect_data():
    try:
        data = request.get_json()
        tarjeta = data.get('tarjeta')
        vehiculos = data.get('vehiculos')
        evento = data.get('evento')

        cursor = db.cursor()

        # Find user by RFID tag
        cursor.execute("SELECT idUsuario FROM usuario WHERE codigoTarjeta = %s", (tarjeta,))
        result = cursor.fetchone()
        if not result:
            cursor.execute("INSERT INTO usuario (nombre, apellido, codigoTarjeta) VALUES (%s, %s, %s)",
                           ("Desconocido", "Desconocido", tarjeta))
            db.commit()
            id_usuario = cursor.lastrowid
        else:
            id_usuario = result[0]

        # Log to historial
        if evento == "entrada":
            cursor.execute("INSERT INTO historial (idUsuario, horaEntrada) VALUES (%s, %s)",
                           (id_usuario, datetime.now()))
        elif evento == "salida":
            cursor.execute("SELECT idHistorial, horaEntrada FROM historial WHERE idUsuario = %s AND horaSalida IS NULL ORDER BY horaEntrada DESC LIMIT 1",
                           (id_usuario,))
            result = cursor.fetchone()
            if result:
                id_historial, hora_entrada = result
                hora_salida = datetime.now()
                duracion = int((hora_salida - hora_entrada).total_seconds() / 60)  # Duration in minutes
                cursor.execute("UPDATE historial SET horaSalida = %s, duracion = %s WHERE idHistorial = %s",
                               (hora_salida, duracion, id_historial))
            else:
                cursor.execute("INSERT INTO historial (idUsuario, horaSalida) VALUES (%s, %s)",
                               (id_usuario, datetime.now()))

        db.commit()
        cursor.close()
        return jsonify({"status": "Datos recibidos"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)