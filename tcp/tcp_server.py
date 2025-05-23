import socket
import mysql.connector
import json
import requests
from datetime import datetime

# MySQL connection

# TCP server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('localhost', 5000))
#server.bind(('0.0.0.0', 12345))
server.listen(1)
print("TCP server running on port 5000")

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
        # cursor.execute("SELECT idUsuario FROM usuario WHERE codigoTarjeta = %s", (sensor_data['rfid'],))
        # user = cursor.fetchone()

        # URL of the API endpoint
        url = "http://localhost:5000/usuario/tarjeta/"+sensor_data['rfid']

        # Make the GET request
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
                # Parse the JSON response
                user = response.json()
                print("JSON Response:", data)
        else:
                print(f"Request failed with status code: {response.status_code}")

        id_usuario = user[0] if user else None
        
        if id_usuario and sensor_data['entrance'] == 90:  # Entrance door opened
            #cursor.execute("INSERT INTO historial (idUsuario, horaEntrada) VALUES (%s, NOW())",(id_usuario,))
            #conn.commit()
            #print(f"Entrada registrada para usuario {id_usuario}")
            r = requests.post('http://localhost:5000/historial/'+id_usuario)
        
        if id_usuario and sensor_data['exit'] == 90:  # Entrance door opened
            r = requests.put('http://localhost:5000/historial/'+id_usuario)
            
            client.close()
    except json.JSONDecodeError:
        print("Error: Invalid JSON data")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()