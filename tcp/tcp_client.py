import socket

# Server address and port
server_address = ('localhost', 5000)

# Create a TCP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    # Connect to the server
    client_socket.connect(server_address)
    print(f"Connected to {server_address}")

    # Send data to the server
    message = "Hello from client"
    client_socket.sendall(message.encode('utf-8'))
    print(f"Sent: {message}")

    # Receive response from the server
    data = client_socket.recv(1024)
    print(f"Received: {data.decode('utf-8')}")

except ConnectionRefusedError:
    print("Connection refused. Make sure the server is running.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the connection
    client_socket.close()
    print("Connection closed")