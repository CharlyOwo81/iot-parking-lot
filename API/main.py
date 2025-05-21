from flask import Flask, jsonify
from flask_mysqldb import MySQL
from datetime import datetime

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'itson'
app.config['MYSQL_DB'] = 'estacionamiento'
mysql = MySQL(app)
if __name__ == '__main__':
    app.run(debug=True)


@app.route('/')
def root():
    return "root"


@app.route("usuario/<int:id>", methods=['GET'])
def getUsuarioPorId(id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * from usuario WHERE idUsuario = %s''', (id,))
    data = cur.fetchALL()

    # si la lista obtenida esta vacia, es decir no se encontro un resultado
    if (not data): jsonify(-1), 404
    else: return jsonify(data), 200

@app.route("usuario/tarjeta/<int:codigoTarjeta>", methods=['GET'])
def getUsuarioPorTarjeta(codigoTarjeta):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * from usuario WHERE codigoTarjeta = %s''', (codigoTarjeta,))
    data = cur.fetchALL()

    # si la lista obtenida esta vacia, es decir no se encontro un resultado
    if (not data): jsonify(-1), 404
    else: return jsonify(data), 200

@app.route("historial/<idUsuario>", methods=['POST'])
def comenzarEstacionamiento(idUsuario):
    cur = mysql.connection.cursor()
    tiempoActual = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute('''INSERT INTO historial (idUsuario, horaEntrada) VALUES (%s, %s)''', (idUsuario, tiempoActual))
    mysql.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Tiempo de estacionamiento comenzado'})

@app.route("historial/<idUsuario>", methods=['PUT'])
def terminarEstacionamiento(idUsuario):
    cur = mysql.connection.cursor()
    tiempoActual = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute('''UPDATE historial SET horaSalida = %s WHERE idUsuario = %s''', (tiempoActual, idUsuario))
    mysql.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Tiempo de estacionamiento terminado'})