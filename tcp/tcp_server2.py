import socket
import requests
import json

HOST = '0.0.0.0'
PORT = 12345

def procesar_mensaje(mensaje):
    mensaje = mensaje.strip()
    try:
        data = json.loads(mensaje)
        if data.get('type') == 'sensorData':
            url = "http://127.0.0.1:5000/sensorData"
            respuesta = requests.post(url, json=data)
            return f"POST SensorData → {respuesta.status_code}: {respuesta.text}"
    except json.JSONDecodeError:
        pass

    if mensaje.startswith("Tarjeta:"):
        valor = mensaje.split(":")[1].strip()
        url = f"http://127.0.0.1:5000/usuario/tarjeta/{valor}"
        respuesta = requests.get(url)
        return f"GET Tarjeta → {respuesta.status_code}: {respuesta.text}"

    elif mensaje.startswith("Comenzar:"):
        valor = mensaje.split(":")[1].strip()
        url = f"http://127.0.0.1:5000/historial/{valor}"
        respuesta = requests.post(url)
        return f"POST Comenzar → {respuesta.status_code}: {respuesta.text}"

    elif mensaje.startswith("Terminar:"):
        valor = mensaje.split(":")[1].strip()
        url = f"http://127.0.0.1:5000/historial/{valor}"
        respuesta = requests.put(url)
        return f"PUT Terminar → {respuesta.status_code}: {respuesta.text}"

    return "Comando no reconocido"

def iniciar_servidor():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"Servidor TCP escuchando en {HOST}:{PORT}...")
        while True:
            client_socket, client_address = server_socket.accept()
            with client_socket:
                print(f"Conexión desde {client_address}")
                data = client_socket.recv(1024).decode()
                print(f"Mensaje recibido: {data}")
                respuesta = procesar_mensaje(data)
                client_socket.sendall(respuesta.encode())

if __name__ == "__main__":
    iniciar_servidor()