import socket

# Dirección y puerto del servidor TCP
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345

def enviar_mensaje(mensaje):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            # Conectarse al servidor
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            print(f"Conectado al servidor en {SERVER_HOST}:{SERVER_PORT}")

            # Enviar mensaje
            client_socket.sendall(mensaje.encode())
            print(f"Mensaje enviado: {mensaje}")

            # Recibir respuesta
            respuesta = client_socket.recv(4096).decode()
            print(f"Respuesta del servidor: {respuesta}")

        except ConnectionRefusedError:
            print("No se pudo conectar con el servidor.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    while True:
        mensaje = input("Escribe un comando (Tarjeta, Usuario, Comenzar, Terminar) o 'salir': ")
        if mensaje.lower() == 'salir':
            break
        enviar_mensaje(mensaje)
