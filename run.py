import socket
import mysql.connector
import json
import requests
from datetime import datetime
from flask import Flask, jsonify
from flask_mysqldb import MySQL
from threading import Thread

import tcp_server as tcp
from API import main as api

def tcp():    
    # MySQL connection
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



def api():        
    app = Flask(__name__)
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = '1234'
    app.config['MYSQL_DB'] = 'estacionamiento'
    mysql = MySQL(app)


    @app.route('/', methods=['GET'])
    def root():
        tiempoActual = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        return tiempoActual

    @app.route('/usuario/<int:id>', methods=['GET'])
    def getUsuarioPorId(id):
        cur = mysql.connection.cursor()
        cur.execute('''SELECT * from usuario WHERE idUsuario = %s''', (id,))
        data = cur.fetchall()
        cur.close()

        # si la lista obtenida esta vacia, es decir no se encontro un resultado
        if (not data): return jsonify(-1), 404
        else: return jsonify(data), 200

    @app.route('/usuario/tarjeta/<string:codigoTarjeta>', methods=['GET'])
    def getIdPorTarjeta(codigoTarjeta):
        cur = mysql.connection.cursor()
        cur.execute('''SELECT * from usuario WHERE codigoTarjeta = %s''', (codigoTarjeta,))
        data = cur.fetchall()
        cur.close()

        # si la lista obtenida esta vacia, es decir no se encontro un resultado
        if (not data): return jsonify({-1}), 404
        else: return jsonify(data[0][0]), 200

    @app.route('/historial/<int:idUsuario>', methods=['POST'])
    def comenzarEstacionamiento(idUsuario):
        cur = mysql.connection.cursor()
        tiempoActual = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute('''INSERT INTO historial (idUsuario, horaEntrada) VALUES (%s, %s)''', (idUsuario, tiempoActual))
        mysql.connection.commit()
        cur.close()
        return jsonify({'mensaje': 'Tiempo de estacionamiento comenzado'})

    @app.route('/historial/<int:idUsuario>', methods=['PUT'])
    def terminarEstacionamiento(idUsuario):
        cur = mysql.connection.cursor()
        tiempoActual = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute('''UPDATE historial SET horaSalida = %s WHERE idUsuario = %s AND horaSalida IS NULL''', (tiempoActual, idUsuario))
        mysql.connection.commit()
        cur.close()
        return jsonify({'mensaje': 'Tiempo de estacionamiento terminado'})

    if __name__ == '__main__':
        app.run(debug=True)

thread_a = Thread(target = api)
thread_b = Thread(target = tcp)

thread_a.start()
thread_b.start()

thread_a.join()
thread_b.join()