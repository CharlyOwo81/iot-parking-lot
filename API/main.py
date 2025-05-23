from flask import Flask, jsonify
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
    if (not data): return jsonify(-1), 404
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