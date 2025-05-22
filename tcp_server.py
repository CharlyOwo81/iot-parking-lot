import socket
import mysql.connector
import json
from datetime import datetime

# MySQL connection
conn = mysql.connector.connect(
            host="mysql.sqlpub.com",
            port=3306,
            user="estacionamiento",
            password="lFLPJzuTlwbCvQnV",
            database="estacionamiento"
)
cursor = conn.cursor()

# TCP server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('0.0.0.0', 12345))
server.listen(1)
print("TCP server running on port 12345")

while True:
    client, addr = server.accept()
    try:
        data = client.recv(1024).decode()
        if not data:
            continue
        sensor_data = json.loads(data)
        
        # Validate required fields
        required_fields = ['spaces', 'rfid', 'entrance', 'exit', 'cajones']
        if not all(field in sensor_data for field in required_fields):
            print("Error: Missing required fields")
            continue
        
        # Find user by RFID code
        cursor.execute("SELECT idUsuario FROM usuario WHERE codigoTarjeta = %s", (sensor_data['rfid'],))
        user = cursor.fetchone()
        id_usuario = user[0] if user else None
        
        if id_usuario and sensor_data['entrance'] == 90:  # Entrance door opened
            cursor.execute(
                "INSERT INTO historial (idUsuario, horaEntrada) VALUES (%s, NOW())",
                (id_usuario,)
            )
            conn.commit()
            print(f"Entrada registrada para usuario {id_usuario}")
        
        client.close()
    except json.JSONDecodeError:
        print("Error: Invalid JSON data")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()