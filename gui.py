import tkinter as tk
import requests
import mysql.connector
from flask import Flask, jsonify, request
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import threading

class ParkingGUI:
    def __init__(self, root):
        # Initialize the main window
        self.root = root
        self.root.title("Parking System")
        self.esp32_ip = "192.168.43.31"  # Replace with ESP32 IP
        self.conn = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="1234",
            database="estacionamiento"
        )
        
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()

        # Canvas for graphical representation
        self.canvas = tk.Canvas(root, width=400, height=200, bg="#F8EEE2")
        self.canvas.pack(pady=10)
        
        # Status labels
        self.spaces_label = tk.Label(root, text="Espacios disponibles: 0", font=("Roboto", 14))
        self.spaces_label.pack()
        self.rfid_label = tk.Label(root, text="RFID: N/A", font=("Roboto", 14))
        self.rfid_label.pack()
        self.user_label = tk.Label(root, text="Usuario: N/A", font=("Roboto", 14))
        self.user_label.pack()
        self.entrance_label = tk.Label(root, text="Entrada: 0°", font=("Roboto", 14))
        self.entrance_label.pack()
        self.exit_label = tk.Label(root, text="Salida: 0°", font=("Roboto", 14))
        self.exit_label.pack()

        # Configurable parameters
        self.config_frame = tk.Frame(root)
        self.config_frame.pack(pady=10)
        tk.Label(self.config_frame, text="Relay Time (ms):", font=("Roboto", 12)).grid(row=0, column=0)
        self.relay_entry = tk.Entry(self.config_frame)
        self.relay_entry.grid(row=0, column=1)
        tk.Label(self.config_frame, text="Unlock Time (ms):", font=("Roboto", 12)).grid(row=1, column=0)
        self.unlock_entry = tk.Entry(self.config_frame)
        self.unlock_entry.grid(row=1, column=1)
        tk.Button(self.config_frame, text="Actualizar", command=self.update_config, bg="#FF4C45", fg="#EAEAEA").grid(row=2, columnspan=2)

        # Plot for historical data
        self.fig = Figure(figsize=(5, 3))
        self.ax = self.fig.add_subplot(111)
        self.canvas_plot = FigureCanvasTkAgg(self.fig, root)
        self.canvas_plot.get_tk_widget().pack()

        # Period selection for statistics
        self.period_frame = tk.Frame(root)
        self.period_frame.pack(pady=10)
        tk.Label(self.period_frame, text="Período (minutos):", font=("Roboto", 12)).grid(row=0, column=0)
        self.period_entry = tk.Entry(self.period_frame)
        self.period_entry.insert(0, "60")
        self.period_entry.grid(row=0, column=1)
        tk.Button(self.period_frame, text="Actualizar Gráfico", command=self.plot_stats, bg="#FF4C45", fg="#EAEAEA").grid(row=0, column=2)

        self.update_gui()

    def update_gui(self):
        try:
            response = requests.get(f"http://{self.esp32_ip}/api/status", timeout=2)
            data = response.json()
            self.spaces_label.config(text=f"Espacios disponibles: {data['spaces']}")
            self.rfid_label.config(text=f"RFID: {data['rfid'] or 'N/A'}")
            self.entrance_label.config(text=f"Entrada: {data['entrance']}°")
            self.exit_label.config(text=f"Salida: {data['exit']}°")
            self.relay_entry.delete(0, tk.END)
            self.relay_entry.insert(0, data['relay_time'])
            self.unlock_entry.delete(0, tk.END)
            self.unlock_entry.insert(0, data['unlock_time'])

            # Get user info
            cursor = self.conn.cursor()
            cursor.execute("SELECT nombre, apellido FROM usuario WHERE codigoTarjeta = %s", (data['rfid'],))
            user = cursor.fetchone()
            self.user_label.config(text=f"Usuario: {user[0] + ' ' + user[1] if user else 'N/A'}")

            # Update graphical representation
            self.canvas.delete("all")
            for i in range(4):
                color = "#FF4C45" if data['cajones'][i] else "#00FF00"
                self.canvas.create_rectangle(50 + i*80, 50, 100 + i*80, 100, fill=color)
                self.canvas.create_text(75 + i*80, 75, text=f"Espacio {i+1}", font=("Roboto", 10))
        except:
            print("Error fetching status")
        self.plot_stats()
        self.root.after(2000, self.update_gui)

    def update_config(self):
        try:
            requests.post(f"http://{self.esp32_ip}/api/config", data={
                "relay_time": self.relay_entry.get(),
                "unlock_time": self.unlock_entry.get()
            }, timeout=2)
            print("Configuración actualizada")
        except:
            print("Error updating config")

    def plot_stats(self):
        try:
            cursor = self.conn.cursor()
            period = int(self.period_entry.get())
            cursor.execute("SELECT timestamp, spaces FROM sensor_data WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s MINUTE) ORDER BY timestamp", (period,))
            data = cursor.fetchall()
            times = [row[0] for row in data]
            spaces = [row[1] for row in data]
            self.ax.clear()
            self.ax.plot(times, spaces, color="#1E90FF")
            self.ax.set_xlabel("Tiempo")
            self.ax.set_ylabel("Espacios")
            self.ax.set_ylim(0, 4)
            self.canvas_plot.draw()
        except:
            print("Error plotting stats")
            
    def run_server(self):
        app = Flask(__name__)
        
        @app.route('/check_rfid', methods=['GET'])
        def check_rfid():
            rfid = request.args.get('tag', '').replace(" ", "").upper()
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM usuario WHERE REPLACE(codigoTarjeta, ' ', '') = %s", (rfid,))

            try:
                cursor.execute("SELECT COUNT(*) FROM usuario WHERE codigoTarjeta = %s", (rfid,))
                count = cursor.fetchone()[0]
                return jsonify(count > 0)
            except Exception as e:
                print(f"Error en consulta: {e}")
                return jsonify(False), 500
    
        app.run(host='0.0.0.0', port=5000, debug=False)

root = tk.Tk()
app = ParkingGUI(root)
root.mainloop()