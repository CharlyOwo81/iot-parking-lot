#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <LittleFS.h>
#include <SPI.h>
#include <MFRC522.h>
#include <HTTPClient.h>

// WiFi configuration
const char *ssid = "Galaxy A03s e8eb";
const char *password = "pqmj0137";

// Flask collector URL
const char *collector_url = "http://192.168.68.113:5000/collect";

// RFID configuration
#define SS_PIN 5
#define RST_PIN 17
MFRC522 mfrc522(SS_PIN, RST_PIN);

// Servo configuration
#define ENTRANCE_SERVO_PIN 33
#define EXIT_SERVO_PIN 27
Servo servoEntrada;
Servo servoSalida;

// DIP switch configuration
#define NUM_CAJONES 3
const int dipPines[NUM_CAJONES] = { 14, 32, 35 };

// Relay configuration
#define RELAY_ENTRADA 21
#define RELAY_DENEGADO 22

// Timing constants
#define RELAY_TIME 1000
#define ENTRANCE_OPEN_TIME 5000
#define EXIT_OPEN_TIME 24000

AsyncWebServer server(80);

// System state
struct Estado {
  String ultimaTarjeta = "N/A";
  int espaciosDisponibles = NUM_CAJONES;
  bool entradaAbierta = false;
  bool salidaAbierta = false;
  bool parkingLleno = false;
  byte systemState = 0;  // 0: Idle, 1: Autorizado, 2: Denegado, 3: Entrada abierta, 4: Salida abierta
  unsigned long previousMillis = 0;
  unsigned long exitMillis = 0;
  bool cajonesAnteriores[NUM_CAJONES] = { false };
  bool triggerSalida = false;
  String seats[NUM_CAJONES + 1] = { "_", "Libre", "Libre", "Libre" };
} estado;

void sendToCollector(String tarjeta, int vehiculos, String evento) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi no conectado, no se envía al colector");
    return;
  }
  HTTPClient http;
  if (!http.begin(collector_url)) {
    Serial.println("Error iniciando HTTP para colector");
    return;
  }
  http.addHeader("Content-Type", "application/json");

  DynamicJsonDocument doc(256);
  doc["tarjeta"] = tarjeta;
  doc["vehiculos"] = vehiculos;
  doc["evento"] = evento;
  String payload;
  serializeJson(doc, payload);

  Serial.println("Enviando a colector: " + payload);
  int httpCode = http.POST(payload);
  if (httpCode == 200) {
    Serial.println("Datos enviados, respuesta: " + http.getString());
  } else {
    Serial.println("Error en colector, código: " + String(httpCode));
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(100);

  // Initialize SPI and RFID
  SPI.begin();
  mfrc522.PCD_Init();
  Serial.println("RFID inicializado");

  // Initialize servos
  servoEntrada.setPeriodHertz(50);
  if (!servoEntrada.attach(ENTRANCE_SERVO_PIN, 500, 2400)) {
    Serial.println("Error al conectar servo de entrada");
  } else {
    Serial.println("Servo de entrada conectado correctamente");
    servoEntrada.write(90);  // Test movement
    delay(1000);
    servoEntrada.write(0);
  }
  servoSalida.setPeriodHertz(50);
  if (!servoSalida.attach(EXIT_SERVO_PIN, 500, 2400)) {
    Serial.println("Error al conectar servo de salida");
  }
  servoEntrada.write(0);  // Closed
  servoSalida.write(0);   // Closed

  // Initialize relays
  pinMode(RELAY_ENTRADA, OUTPUT);
  pinMode(RELAY_DENEGADO, OUTPUT);
  digitalWrite(RELAY_ENTRADA, LOW);
  digitalWrite(RELAY_DENEGADO, LOW);

  // Initialize DIP switches
  for (int i = 0; i < NUM_CAJONES; i++) {
    pinMode(dipPines[i], INPUT_PULLDOWN);
    estado.cajonesAnteriores[i] = false;
  }

  // Initialize LittleFS
  if (!LittleFS.begin(true)) {
    Serial.println("Error al montar LittleFS");
    return;
  }
  Serial.println("LittleFS montado");

  // List files in LittleFS for debugging
  File root = LittleFS.open("/");
  File file = root.openNextFile();
  while (file) {
    Serial.println("Archivo: " + String(file.name()));
    file = root.openNextFile();
  }

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi...");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nFallo al conectar a WiFi");
    return;
  }
  Serial.println("\nConectado a WiFi, IP: " + WiFi.localIP().toString());

  // Serve static files with debug logging
  server.serveStatic("/", LittleFS, "/")
    .setDefaultFile("index.html")
    .setCacheControl("max-age=600")
    .setFilter([](AsyncWebServerRequest *request) -> bool {
      Serial.println("Solicitud estática: " + request->url());
      return true;
    });

  // Configure API endpoints
  server.on("/api/status", HTTP_GET, [](AsyncWebServerRequest *request) {
    Serial.println("Solicitud recibida en /api/status");
    DynamicJsonDocument doc(512);
    doc["ultimaTarjeta"] = estado.ultimaTarjeta;
    doc["espaciosDisponibles"] = estado.espaciosDisponibles;
    doc["entradaAbierta"] = estado.entradaAbierta;
    doc["salidaAbierta"] = estado.salidaAbierta;
    doc["parkingLleno"] = estado.parkingLleno;
    JsonArray cajones = doc.createNestedArray("cajones");
    for (int i = 0; i < NUM_CAJONES; i++) {
      JsonObject c = cajones.createNestedObject();
      c["id"] = i + 1;
      c["estado"] = estado.seats[i + 1];
    }
    String json;
    serializeJson(doc, json);
    request->send(200, "application/json", json);
  });

  server.on(
    "/api/control", HTTP_POST, [](AsyncWebServerRequest *request) {},
    NULL,
    [](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
      static String body = "";
      if (index == 0) body = "";  // Reset for new request
      for (size_t i = 0; i < len; i++) {
        body += (char)data[i];
      }
      if (index + len == total) {  // Complete body received
        Serial.println("POST /api/control: " + body);
        DynamicJsonDocument doc(256);
        DeserializationError error = deserializeJson(doc, body);
        if (error) {
          Serial.println("Error de JSON: " + String(error.c_str()));
          request->send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
          return;
        }
        String action = doc["action"] | "";
        if (action == "open_entrance" && estado.espaciosDisponibles > 0) {
          digitalWrite(RELAY_ENTRADA, HIGH);
          estado.previousMillis = millis();
          estado.systemState = 1;
          request->send(200, "application/json", "{\"status\":\"Entrada abriendo\"}");
        } else if (action == "open_exit") {
          servoSalida.write(90);
          estado.salidaAbierta = true;
          estado.exitMillis = millis();
          estado.systemState = 4;
          Serial.println("Salida abierta, Servo angle: " + String(servoSalida.read()));
          sendToCollector(estado.ultimaTarjeta, NUM_CAJONES - estado.espaciosDisponibles, "salida");
          request->send(200, "application/json", "{\"status\":\"Salida abriendo\"}");
        } else {
          request->send(400, "application/json", "{\"error\":\"Acción inválida o sin espacios\"}");
        }
        body = "";  // Clear after processing
      }
    });

  server.on("/api/reset", HTTP_POST, [](AsyncWebServerRequest *request) {
    servoEntrada.write(0);
    servoSalida.write(0);
    estado.entradaAbierta = false;
    estado.salidaAbierta = false;
    estado.systemState = 0;
    estado.ultimaTarjeta = "N/A";
    estado.triggerSalida = false;
    digitalWrite(RELAY_ENTRADA, LOW);
    digitalWrite(RELAY_DENEGADO, LOW);
    request->send(200, "application/json", "{\"status\":\"Sistema reiniciado\"}");
  });

  server.onNotFound([](AsyncWebServerRequest *request) {
    Serial.println("Not found: " + request->url());
    request->send(404, "application/json", "{\"error\":\"Not found\"}");
  });

  // Explicit routes for index and status
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    if (LittleFS.exists("/index.html")) {
      Serial.println("Serving: /index.html");
      request->send(LittleFS, "/index.html", "text/html");
    } else {
      request->send(404, "text/plain", "index.html not found");
    }
  });

  server.on("/status", HTTP_GET, [](AsyncWebServerRequest *request) {
    if (LittleFS.exists("/status.html")) {
      Serial.println("Serving: /status.html");
      request->send(LittleFS, "/status.html", "text/html");
    } else {
      request->send(404, "text/plain", "status.html not found");
    }
  });

  server.begin();
  Serial.println("Servidor iniciado");
}

void loop() {
  unsigned long currentMillis = millis();

  // State machine
  switch (estado.systemState) {
    case 1:  // Autorizado (entry)
      if (currentMillis - estado.previousMillis >= RELAY_TIME) {
        digitalWrite(RELAY_ENTRADA, LOW);
        servoEntrada.write(90);
        estado.entradaAbierta = true;
        estado.previousMillis = currentMillis;
        estado.systemState = 3;
        Serial.println("Entrada abierta, Servo angle: " + String(servoEntrada.read()));
        sendToCollector(estado.ultimaTarjeta, NUM_CAJONES - estado.espaciosDisponibles, "entrada");
      }
      break;
    case 2:  // Denegado
      if (currentMillis - estado.previousMillis >= RELAY_TIME) {
        digitalWrite(RELAY_DENEGADO, LOW);
        estado.systemState = 0;
      }
      break;
    case 3:  // Entrada abierta
      if (currentMillis - estado.previousMillis >= ENTRANCE_OPEN_TIME) {
        servoEntrada.write(0);
        estado.entradaAbierta = false;
        estado.systemState = 0;
        Serial.println("Entrada cerrada");
      }
      break;
    case 4:  // Salida abierta
      if (currentMillis - estado.exitMillis >= EXIT_OPEN_TIME) {
        servoSalida.write(0);
        estado.salidaAbierta = false;
        estado.systemState = 0;
        Serial.println("Salida cerrada");
      }
      break;
    default:  // Idle
      checkRFID();
      break;
  }

  // Update parking slots
  static unsigned long lastCajonUpdate = 0;
  if (currentMillis - lastCajonUpdate >= 100) {
    lastCajonUpdate = currentMillis;
    int newEspacios = 0;
    for (int i = 0; i < NUM_CAJONES; i++) {
      bool estadoActual = !digitalRead(dipPines[i]);
      if (!estadoActual && estado.cajonesAnteriores[i]) {  // Liberado
        estado.triggerSalida = true;
        Serial.println("Cajón " + String(i + 1) + " liberado");
      }
      estado.cajonesAnteriores[i] = estadoActual;
      estado.seats[i + 1] = estadoActual ? "Ocupado" : "Libre";
      if (!estadoActual) newEspacios++;
    }
    if (newEspacios != estado.espaciosDisponibles) {
      estado.espaciosDisponibles = newEspacios;
      estado.parkingLleno = (estado.espaciosDisponibles == 0);
      if (estado.parkingLleno) Serial.println("ALERTA: Estacionamiento lleno");
    }
  }

  // Handle automatic exit door opening
  if (estado.triggerSalida && estado.espaciosDisponibles > 0 && !estado.salidaAbierta) {
    servoSalida.write(90);
    estado.salidaAbierta = true;
    estado.exitMillis = currentMillis;
    estado.systemState = 4;
    estado.triggerSalida = false;
    Serial.println("Salida abierta por liberación de espacio");
    sendToCollector(estado.ultimaTarjeta, NUM_CAJONES - estado.espaciosDisponibles, "salida");
  }
}

void checkRFID() {
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) return;

  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uid.concat(String(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " "));
    uid.concat(String(mfrc522.uid.uidByte[i], HEX));
  }
  uid.toUpperCase();
  estado.ultimaTarjeta = uid.substring(1);
  Serial.println("UID detectado: " + estado.ultimaTarjeta);

  if (estado.espaciosDisponibles > 0 && estado.ultimaTarjeta == "A3 3E 3B CD") {
    Serial.println("Acceso autorizado");
    digitalWrite(RELAY_ENTRADA, HIGH);
    estado.previousMillis = millis();
    estado.systemState = 1;
  } else {
    Serial.println("Acceso denegado");
    digitalWrite(RELAY_DENEGADO, HIGH);
    estado.previousMillis = millis();
    estado.systemState = 2;
  }
}