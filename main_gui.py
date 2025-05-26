import tkinter as tk
from tkinter import messagebox, ttk
import requests
import threading
import time
import mysql.connector
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ParkingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Estacionamiento")
        self.root.geometry("1000x750")  # Larger for better layout
        self.esp32_ip = "192.168.68.32"
        self.running = True
        self.is_dark_theme = True

        # Database connection
        self.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="estacionamiento"
        )

        # Color scheme
        self.colors = {
            "bg_dark": "#1C2526",      # Soft dark background
            "bg_light": "#E8ECEF",     # Light gray
            "fg_dark": "#F4F4F9",      # Off-white text
            "fg_light": "#2D2D34",     # Dark gray text
            "accent": "#2EC4B6",       # Vibrant teal
            "alert": "#FF6B6B",        # Coral alert
            "card_bg": "#28333A",      # Darker card
            "card_bg_light": "#DDE1E4",# Light card
            "button_bg": "#2EC4B6",    # Teal buttons
            "button_fg": "#FFFFFF",    # White button text
            "button_hover": "#28A99E"  # Darker teal hover
        }

        # Apply initial theme
        self.apply_theme()

        # Main frame
        self.main_frame = tk.Frame(self.root, bg=self.colors["bg_dark"])
        self.main_frame.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.main_frame, bg=self.colors["card_bg"], width=250)
        self.sidebar.pack(side="left", fill="y", padx=15, pady=15)

        # Content area
        self.content = tk.Frame(self.main_frame, bg=self.colors["bg_dark"])
        self.content.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        # Sidebar elements
        tk.Label(self.sidebar, text="Panel de Control", font=("Helvetica", 18, "bold"), fg=self.colors["fg_dark"], bg=self.colors["card_bg"]).pack(pady=20)
        
        self.btn_entrada = tk.Button(self.sidebar, text="🚪 Abrir Entrada", command=self.abrir_entrada, font=("Helvetica", 14, "bold"),
                                     bg=self.colors["button_bg"], fg=self.colors["button_fg"], activebackground=self.colors["button_hover"],
                                     relief="flat", padx=25, pady=12, cursor="hand2")
        self.btn_entrada.pack(pady=10, padx=15, fill="x")
        self.btn_entrada.bind("<Enter>", lambda e: self.btn_entrada.config(bg=self.colors["button_hover"]))
        self.btn_entrada.bind("<Leave>", lambda e: self.btn_entrada.config(bg=self.colors["button_bg"]))
        self.label_entrada_status = tk.Label(self.sidebar, text="", font=("Helvetica", 10), fg=self.colors["fg_dark"], bg=self.colors["card_bg"])
        self.label_entrada_status.pack(pady=5)

        self.btn_salida = tk.Button(self.sidebar, text="🚪 Abrir Salida", command=self.abrir_salida, font=("Helvetica", 14, "bold"),
                                    bg=self.colors["button_bg"], fg=self.colors["button_fg"], activebackground=self.colors["button_hover"],
                                    relief="flat", padx=25, pady=12, cursor="hand2")
        self.btn_salida.pack(pady=10, padx=15, fill="x")
        self.btn_salida.bind("<Enter>", lambda e: self.btn_salida.config(bg=self.colors["button_hover"]))
        self.btn_salida.bind("<Leave>", lambda e: self.btn_salida.config(bg=self.colors["button_bg"]))
        self.label_salida_status = tk.Label(self.sidebar, text="", font=("Helvetica", 10), fg=self.colors["fg_dark"], bg=self.colors["card_bg"])
        self.label_salida_status.pack(pady=5)

        self.btn_graph = tk.Button(self.sidebar, text="📊 Gráfico de Uso", command=self.mostrar_grafico, font=("Helvetica", 14, "bold"),
                                   bg=self.colors["button_bg"], fg=self.colors["button_fg"], activebackground=self.colors["button_hover"],
                                   relief="flat", padx=25, pady=12, cursor="hand2")
        self.btn_graph.pack(pady=10, padx=15, fill="x")
        self.btn_graph.bind("<Enter>", lambda e: self.btn_graph.config(bg=self.colors["button_hover"]))
        self.btn_graph.bind("<Leave>", lambda e: self.btn_graph.config(bg=self.colors["button_bg"]))

        self.btn_theme = tk.Button(self.sidebar, text="🌙 Cambiar Tema", command=self.toggle_theme, font=("Helvetica", 14, "bold"),
                                   bg=self.colors["button_bg"], fg=self.colors["button_fg"], activebackground=self.colors["button_hover"],
                                   relief="flat", padx=25, pady=12, cursor="hand2")
        self.btn_theme.pack(pady=10, padx=15, fill="x")
        self.btn_theme.bind("<Enter>", lambda e: self.btn_theme.config(bg=self.colors["button_hover"]))
        self.btn_theme.bind("<Leave>", lambda e: self.btn_theme.config(bg=self.colors["button_bg"]))

        # Status cards
        self.status_frame = tk.Frame(self.content, bg=self.colors["bg_dark"])
        self.status_frame.pack(fill="x", pady=15)

        self.card_tarjeta = tk.Frame(self.status_frame, bg=self.colors["card_bg"], bd=2, relief="groove")
        self.card_tarjeta.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.label_tarjeta = tk.Label(self.card_tarjeta, text="Última Tarjeta: N/A", font=("Helvetica", 12), fg=self.colors["fg_dark"], bg=self.colors["card_bg"])
        self.label_tarjeta.pack(pady=15, padx=15)

        self.card_espacios = tk.Frame(self.status_frame, bg=self.colors["card_bg"], bd=2, relief="groove")
        self.card_espacios.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.label_espacios = tk.Label(self.card_espacios, text="Espacios Disponibles: N/A", font=("Helvetica", 12), fg=self.colors["fg_dark"], bg=self.colors["card_bg"])
        self.label_espacios.pack(pady=15, padx=15)

        self.card_entrada = tk.Frame(self.status_frame, bg=self.colors["card_bg"], bd=2, relief="groove")
        self.card_entrada.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.label_entrada = tk.Label(self.card_entrada, text="Puerta Entrada: N/A", font=("Helvetica", 12), fg=self.colors["fg_dark"], bg=self.colors["card_bg"])
        self.label_entrada.pack(pady=15, padx=15)

        self.card_salida = tk.Frame(self.status_frame, bg=self.colors["card_bg"], bd=2, relief="groove")
        self.card_salida.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.label_salida = tk.Label(self.card_salida, text="Puerta Salida: N/A", font=("Helvetica", 12), fg=self.colors["fg_dark"], bg=self.colors["card_bg"])
        self.label_salida.pack(pady=15, padx=15)

        # Cajones and Alert
        self.card_cajones = tk.Frame(self.content, bg=self.colors["card_bg"], bd=2, relief="groove")
        self.card_cajones.pack(fill="x", pady=10)
        self.label_cajones = tk.Label(self.card_cajones, text="Cajones: N/A", font=("Helvetica", 12), fg=self.colors["fg_dark"], bg=self.colors["card_bg"])
        self.label_cajones.pack(pady=15, padx=15)

        self.label_alerta = tk.Label(self.content, text="", font=("Helvetica", 12, "bold"), fg=self.colors["alert"], bg=self.colors["bg_dark"])
        self.label_alerta.pack(pady=10)

        # History table
        tk.Label(self.content, text="Historial de Accesos", font=("Helvetica", 16, "bold"), fg=self.colors["fg_dark"], bg=self.colors["bg_dark"]).pack(pady=10)
        self.history_frame = tk.Frame(self.content, bg=self.colors["bg_dark"])
        self.history_frame.pack(fill="both", expand=True, pady=10)

        style = ttk.Style()
        style.configure("Custom.Treeview", background=self.colors["card_bg"], foreground=self.colors["fg_dark"], fieldbackground=self.colors["card_bg"], font=("Helvetica", 11))
        style.configure("Custom.Treeview.Heading", font=("Helvetica", 12, "bold"), background=self.colors["button_bg"], foreground=self.colors["button_fg"])

        self.tree = ttk.Treeview(self.history_frame, columns=("ID", "Nombre", "Entrada", "Salida", "Duración"), show="headings", style="Custom.Treeview")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Entrada", text="Entrada")
        self.tree.heading("Salida", text="Salida")
        self.tree.heading("Duración", text="Duración (min)")
        self.tree.column("ID", width=60, anchor="center")
        self.tree.column("Nombre", width=200, anchor="w")
        self.tree.column("Entrada", width=180, anchor="center")
        self.tree.column("Salida", width=180, anchor="center")
        self.tree.column("Duración", width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Start auto-refresh
        self.thread = threading.Thread(target=self.actualizar_datos)
        self.thread.daemon = True
        self.thread.start()

    def apply_theme(self):
        bg = self.colors["bg_dark"] if self.is_dark_theme else self.colors["bg_light"]
        fg = self.colors["fg_dark"] if self.is_dark_theme else self.colors["fg_light"]
        card_bg = self.colors["card_bg"] if self.is_dark_theme else self.colors["card_bg_light"]
        self.root.config(bg=bg)
        self.colors["current_bg"] = bg
        self.colors["current_fg"] = fg
        self.colors["current_card_bg"] = card_bg

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()
        # Update widgets
        self.main_frame.config(bg=self.colors["current_bg"])
        self.sidebar.config(bg=self.colors["current_card_bg"])
        self.content.config(bg=self.colors["current_bg"])
        self.status_frame.config(bg=self.colors["current_bg"])
        self.card_tarjeta.config(bg=self.colors["current_card_bg"])
        self.card_espacios.config(bg=self.colors["current_card_bg"])
        self.card_entrada.config(bg=self.colors["current_card_bg"])
        self.card_salida.config(bg=self.colors["current_card_bg"])
        self.card_cajones.config(bg=self.colors["current_card_bg"])
        self.history_frame.config(bg=self.colors["current_bg"])
        for widget in [self.label_tarjeta, self.label_espacios, self.label_entrada, self.label_salida, self.label_cajones]:
            widget.config(bg=self.colors["current_card_bg"], fg=self.colors["current_fg"])
        self.label_alerta.config(bg=self.colors["current_bg"], fg=self.colors["alert"])
        for widget in self.sidebar.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(bg=self.colors["current_card_bg"], fg=self.colors["current_fg"])
        style = ttk.Style()
        style.configure("Custom.Treeview", background=self.colors["current_card_bg"], foreground=self.colors["current_fg"], fieldbackground=self.colors["current_card_bg"], font=("Helvetica", 11))
        style.configure("Custom.Treeview.Heading", font=("Helvetica", 12, "bold"), background=self.colors["button_bg"], foreground=self.colors["button_fg"])

    def actualizar_datos(self):
        while self.running:
            try:
                # Update API status
                response = requests.get(f"http://{self.esp32_ip}/api/status", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.root.after(0, self.actualizar_gui, data)

                # Update historial
                cursor = self.db.cursor()
                cursor.execute("""
                    SELECT h.idHistorial, u.nombre, u.apellido, h.horaEntrada, h.horaSalida, h.duracion
                    FROM historial h
                    JOIN usuario u ON h.idUsuario = u.idUsuario
                    ORDER BY h.idHistorial DESC LIMIT 5
                """)
                results = cursor.fetchall()
                cursor.close()

                self.root.after(0, self.actualizar_historial, results)

            except (requests.RequestException, mysql.connector.Error) as e:
                self.root.after(0, self.mostrar_error, str(e))
            time.sleep(5)

    def actualizar_gui(self, data):
        self.label_tarjeta.config(text=f"Última Tarjeta: {data['ultimaTarjeta']}")
        self.label_espacios.config(text=f"Espacios Disponibles: {data['espaciosDisponibles']}")
        self.label_entrada.config(text=f"Puerta Entrada: {'Abierta' if data['entradaAbierta'] else 'Cerrada'}")
        self.label_salida.config(text=f"Puerta Salida: {'Abierta' if data['salidaAbierta'] else 'Cerrada'}")
        cajones_text = "Cajones: " + ", ".join([f"Cajón {c['id']}: {c['estado']}" for c in data['cajones']])
        self.label_cajones.config(text=cajones_text)
        self.label_alerta.config(text="ALERTA: Estacionamiento lleno" if data['parkingLleno'] else "")

    def actualizar_historial(self, results):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in results:
            id_historial, nombre, apellido, entrada, salida, duracion = row
            entrada_str = entrada.strftime("%Y-%m-%d %H:%M:%S") if entrada else "N/A"
            salida_str = salida.strftime("%Y-%m-%d %H:%M:%S") if salida else "N/A"
            duracion_str = f"{duracion}" if duracion is not None else "N/A"
            self.tree.insert("", "end", values=(id_historial, f"{nombre} {apellido}", entrada_str, salida_str, duracion_str))

    def mostrar_error(self, error):
        self.label_alerta.config(text=f"Error: {error}")

    def abrir_entrada(self):
        self.label_entrada_status.config(text="Abriendo...")
        self.root.update()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(f"http://{self.esp32_ip}/api/control", json={"action": "open_entrance"}, timeout=5)
                if response.status_code == 200:
                    self.label_entrada_status.config(text="¡Abierto!")
                    messagebox.showinfo("Éxito", response.json().get("status", "Entrada abriendo"))
                    self.root.after(2000, lambda: self.label_entrada_status.config(text=""))
                    return
                else:
                    self.label_entrada_status.config(text=f"Error (Intento {attempt+1})")
                    messagebox.showerror("Error", response.json().get("error", "Fallo al abrir entrada"))
            except requests.RequestException as e:
                self.label_entrada_status.config(text=f"Error (Intento {attempt+1})")
                messagebox.showerror("Error", f"No se pudo conectar: {e}")
            time.sleep(1)
        self.label_entrada_status.config(text="Fallo tras 3 intentos")
        self.root.after(2000, lambda: self.label_entrada_status.config(text=""))

    def abrir_salida(self):
        self.label_salida_status.config(text="Abriendo...")
        self.root.update()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(f"http://{self.esp32_ip}/api/control", json={"action": "open_exit"}, timeout=5)
                if response.status_code == 200:
                    self.label_salida_status.config(text="¡Abierto!")
                    messagebox.showinfo("Éxito", response.json().get("status", "Salida abriendo"))
                    self.root.after(2000, lambda: self.label_salida_status.config(text=""))
                    return
                else:
                    self.label_salida_status.config(text=f"Error (Intento {attempt+1})")
                    messagebox.showerror("Error", response.json().get("error", "Fallo al abrir salida"))
            except requests.RequestException as e:
                self.label_salida_status.config(text=f"Error (Intento {attempt+1})")
                messagebox.showerror("Error", f"No se pudo conectar: {e}")
            time.sleep(1)
        self.label_salida_status.config(text="Fallo tras 3 intentos")
        self.root.after(2000, lambda: self.label_salida_status.config(text=""))

    def mostrar_grafico(self):
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT h.idHistorial, h.duracion
                FROM historial h
                WHERE h.duracion IS NOT NULL
                ORDER BY h.idHistorial DESC LIMIT 10
            """)
            results = cursor.fetchall()
            cursor.close()

            if not results:
                messagebox.showinfo("Sin Datos", "No hay datos de duración para mostrar en el gráfico.")
                return

            # Prepare data
            labels = [f"ID {row[0]}" for row in results]
            durations = [row[1] for row in results]

            # Create popup window
            graph_window = tk.Toplevel(self.root)
            graph_window.title("Gráfico de Uso del Estacionamiento")
            graph_window.geometry("900x600")
            graph_window.config(bg=self.colors["current_bg"])

            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6), facecolor=self.colors["current_bg"])
            ax.bar(labels, durations, color=self.colors["accent"], edgecolor=self.colors["button_fg"])
            ax.set_xlabel("ID de Historial", color=self.colors["current_fg"], fontsize=14)
            ax.set_ylabel("Duración (minutos)", color=self.colors["current_fg"], fontsize=14)
            ax.set_title("Uso del Estacionamiento por Duración", color=self.colors["current_fg"], fontsize=16)
            ax.set_facecolor(self.colors["current_card_bg"])
            ax.tick_params(colors=self.colors["current_fg"])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color(self.colors["current_fg"])
            ax.spines['bottom'].set_color(self.colors["current_fg"])
            plt.xticks(rotation=45, ha='right', color=self.colors["current_fg"])
            plt.tight_layout()

            # Display in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=graph_window)
            canvas.draw()
            canvas.get_tk_widget().pack(pady=15, fill="both", expand=True)

            # Close button
            btn_close = tk.Button(graph_window, text="Cerrar", command=graph_window.destroy, font=("Helvetica", 12, "bold"),
                                  bg=self.colors["button_bg"], fg=self.colors["button_fg"], relief="flat", padx=25, pady=12)
            btn_close.pack(pady=15)

        except mysql.connector.Error as e:
            messagebox.showerror("Error", f"No se pudo obtener datos: {e}")

    def cerrar(self):
        self.running = False
        self.db.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ParkingGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.cerrar)
    root.mainloop()