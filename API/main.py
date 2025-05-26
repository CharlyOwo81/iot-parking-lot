from flask import Flask, jsonify, request
from flask_mysqldb import MySQL
from datetime import datetime

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'estacionamiento'
mysql = MySQL(app)

@app.route('/', methods=['GET'])
def root():
    return datetime.today().strftime('%Y-%m-%d %H:%M:%S')

@app.route('/usuario/<int:id>', methods=['GET'])
def getUsuarioPorId(id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM usuario WHERE idUsuario = %s''', (id,))
    data = cur.fetchall()
    cur.close()
    if not data:
        return jsonify(-1), 404
    return jsonify(data), 200

@app.route('/usuario/tarjeta/<string:codigoTarjeta>', methods=['GET'])
def getIdPorTarjeta(codigoTarjeta):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM usuario WHERE codigoTarjeta = %s''', (codigoTarjeta,))
    data = cur.fetchall()
    cur.close()
    if not data:
        return jsonify(-1), 404
    return jsonify(data[0][0]), 200

@app.route('/historial/<int:idUsuario>', methods=['POST'])
def comenzarEstacionamiento(idUsuario):
    cur = mysql.connection.cursor()
    tiempoActual = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute('''INSERT INTO historial (idUsuario, horaEntrada) VALUES (%s, %s)''', (idUsuario, tiempoActual))
    mysql.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Tiempo de estacionamiento comenzado'}), 200

@app.route('/historial/<int:idUsuario>', methods=['PUT'])
def terminarEstacionamiento(idUsuario):
    cur = mysql.connection.cursor()
    tiempoActual = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute('''UPDATE historial SET horaSalida = %s WHERE idUsuario = %s AND horaSalida IS NULL''', (tiempoActual, idUsuario))
    mysql.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Tiempo de estacionamiento terminado'}), 200

@app.route('/sensorData', methods=['POST'])
def storeSensorData():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute('''INSERT INTO sensor_data (espaciosDisponibles, systemState, timestamp) 
                   VALUES (%s, %s, %s)''', 
                (data['espaciosDisponibles'], data['systemState'], datetime.fromtimestamp(data['timestamp'])))
    mysql.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Datos de sensores almacenados'}), 200

@app.route('/params', methods=['GET'])
def getParams():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM params WHERE id = 1''')
    data = cur.fetchall()
    cur.close()
    return jsonify({'relayTime': data[0][1], 'unlockTime': data[0][2]}), 200

@app.route('/params', methods=['POST'])
def setParams():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute('''UPDATE params SET relayTime = %s, unlockTime = %s WHERE id = 1''', 
                (data['relayTime'], data['unlockTime']))
    mysql.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Parámetros actualizados'}), 200

if __name__ == '__main__':
    app.run(debug=True)