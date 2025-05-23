  #include <SPI.h>
  #include <MFRC522.h>
  #include <ESP32Servo.h>
  #include <EEPROM.h>
  #include <WiFi.h>
  #include <WiFiUdp.h>
  #include <NTPClient.h>
  #include <WiFiClient.h>
  #include <HTTPClient.h>

  // Configuración WiFi
  const char* ssid = "Huawei de Gamaliel";  // Nombre de tu WiFi
  const char* password = "123456789";       // Contraseña

  // Configuración DIP Switch y LEDs
  #define NUM_CAJONES 3
  const int dipPines[NUM_CAJONES] = { 13, 32, 35 };  // Pines DIP switches

  // Configuración RFID
  #define SS_PIN 5
  #define RST_PIN 17
  MFRC522 mfrc522(SS_PIN, RST_PIN);

  // Configuración Servomotores
  #define ENTRANCE_SERVO_PIN 26
  #define EXIT_SERVO_PIN 27
  Servo entranceDoor;
  Servo exitDoor;

  // Configuración de horario (CAMBIA ESTAS LÍNEAS)
  #define HORA_APERTURA 6 * 60 + 30  // 6:30 AM = 390 minutos
  #define HORA_CIERRE 19 * 60 + 30
  bool dentroDeHorario = false;

  // Tiempos configurables
  #define RELAY_TIME 1000         // Tiempo activación relay
  #define UNLOCK_TIME 5000        // Tiempo puerta abierta entrada
  #define EXIT_UNLOCK_TIME 10000  // Tiempo puerta abierta salida

  // Configuración NTP
  WiFiUDP ntpUDP;
  NTPClient timeClient(ntpUDP, "pool.ntp.org", -7 * 3600, 60000);  // UTC-6 (México), actualiza cada 60 seg


  //Configuración WiFi Client
  WiFiClient client;

  // Variables de control
  unsigned long previousMillis = 0;
  unsigned long exitMillis = 0;
  byte systemState = 0;  // 0: Idle, 1: Autorizado, 2: Denegado, 3: Puerta abierta entrada, 4: Salida activa
  bool exitActive = false;
  int espaciosDisponibles = 0;
  bool espacioLiberado = false;
  bool procesandoSalida = false;  // Nueva variable de control
  char lastRFID[18] = "";
  bool exitTriggers[NUM_CAJONES] = {false};  // Array para triggers individuales
  int currentExitIndex = -1;   

  bool verificarHorario() {
    timeClient.update();  // Actualizar hora desde NTP

    int hora = timeClient.getHours();
    int minutos = timeClient.getMinutes();

    // Convertir a minutos desde medianoche
    int minutosActuales = hora * 60 + minutos;
    return (minutosActuales >= HORA_APERTURA && minutosActuales < HORA_CIERRE);
  }

  void setup() {
    Serial.begin(9600);

    // Conectar a WiFi
    WiFi.begin(ssid, password);
    Serial.print("Conectando a WiFi");
    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
    }
    Serial.println("\nConectado!");

    // Iniciar cliente NTP
    timeClient.begin();
    timeClient.forceUpdate();  // Forzar primera actualización

    // Inicializar EEPROM
    EEPROM.begin(512);

    // Configurar pines DIP
    for (int i = 0; i < NUM_CAJONES; i++) {
      pinMode(dipPines[i], INPUT_PULLDOWN);
    }

    // Configurar RFID
    SPI.begin();
    mfrc522.PCD_Init();
    Serial.println("RFID inicializado");

    // Configurar servomotores
    entranceDoor.attach(ENTRANCE_SERVO_PIN);
    exitDoor.attach(EXIT_SERVO_PIN);
    lockAllDoors();

    // Configurar relays
    pinMode(21, OUTPUT);  // Rele entrada
    pinMode(22, OUTPUT);  // Rele denegado

    Serial.println("Sistema de estacionamiento iniciado");
    Serial.print("Horario: ");
    Serial.print(HORA_APERTURA / 60);
    Serial.print(":00 - ");
    Serial.print(HORA_CIERRE / 60);
    Serial.println(":00");
  }

  void loop() {
    unsigned long currentMillis = millis();


    static unsigned long ultimoReporte = 0;
    if (millis() - ultimoReporte >= 5000) {
      ultimoReporte = millis();
      Serial.print("Hora real: ");
      Serial.print(timeClient.getFormattedTime());
      Serial.print(" | Estado: ");
      Serial.println(dentroDeHorario ? "Abierto" : "Cerrado");
    }

    // Máquina de estados
    switch (systemState) {
      case 1:  // Acceso autorizado (entrada)
        if (currentMillis - previousMillis >= RELAY_TIME) {
          digitalWrite(21, LOW);
          unlockDoor(entranceDoor);
          previousMillis = currentMillis;
          systemState = 3;
        }
        break;

      case 2:  // Acceso denegado
        if (currentMillis - previousMillis >= RELAY_TIME) {
          digitalWrite(22, LOW);
          systemState = 0;
        }
        break;

      case 3:  // Puerta entrada abierta
        if (currentMillis - previousMillis >= UNLOCK_TIME) {
          lockDoor(entranceDoor);
          systemState = 0;
        }
        break;

      case 4:  // Salida activa
        if (currentMillis - exitMillis >= EXIT_UNLOCK_TIME) {
          lockDoor(exitDoor);
          exitActive = false;
          systemState = 0;
          procesandoSalida = false;  // Permitir nuevos triggers
          Serial.println("Puerta de salida cerrada");
        }
        break;

      default:  // Estado idle
        checkRFID();
        break;
    }

    controlSalida(currentMillis);
    actualizarCajones(currentMillis);
    verificarLlenado(currentMillis);

    static unsigned long lastSend = 0;
    if (millis() - lastSend >= 2000) {  // Enviar datos cada 2 segundos
      sendToServer();
      lastSend = millis();
    }
  }

  void checkRFID() {
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) return;

    dentroDeHorario = verificarHorario();
    bool estacionamientoLleno = (espaciosDisponibles == 0);

    // Verificar restricciones primero
    if (estacionamientoLleno) {
      Serial.println("Acceso denegado: Estacionamiento lleno");
      digitalWrite(22, HIGH);
      previousMillis = millis();
      systemState = 2;
      return;
    }

    if (!dentroDeHorario) {
      Serial.println("Acceso denegado: Fuera de horario");
      digitalWrite(22, HIGH);
      previousMillis = millis();
      systemState = 2;
      return;
    }

    // Procesar RFID
    memset(lastRFID, 0, sizeof(lastRFID));  // Limpiar buffer
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      char buffer[3];
      snprintf(buffer, sizeof(buffer), "%02X", mfrc522.uid.uidByte[i]);
      strcat(lastRFID, buffer);
      if (i < mfrc522.uid.size - 1) strcat(lastRFID, " ");
    }

    Serial.print("UID detectado: ");
    Serial.println(lastRFID);


    // Reemplazar la comparación hardcoded por consulta a la DB
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      String rfidSinEspacios = String(lastRFID);      
      http.begin("http://192.168.43.243:5000/usuario/tarjeta/" + rfidSinEspacios);
      http.setTimeout(5000);  // Timeout de 5 segundos
      
      int httpCode = http.GET();
      Serial.print("Código HTTP: ");
      Serial.println(httpCode);
      
      if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        payload.trim();  // Eliminar espacios/retornos
        Serial.print("Respuesta: ");
        Serial.println(payload);
        
        if (payload == "true") {
          // Acceso autorizado
          digitalWrite(21, HIGH);
          systemState = 1;
        } else {
          digitalWrite(22, HIGH);
          systemState = 2;
        }
      } else {
        Serial.println("Error consultando la DB");
        previousMillis = millis();
        systemState = 2;
      }
      http.end();
    } else {
      Serial.println("WiFi desconectado");
    }
  }

  void controlSalida(unsigned long currentMillis) {
    // Buscar el próximo trigger pendiente
    if (!procesandoSalida) {
      for (int i = 0; i < NUM_CAJONES; i++) {
        if (exitTriggers[i]) {
          currentExitIndex = i;
          procesandoSalida = true;
          exitTriggers[i] = false;  // Resetear trigger
          exitMillis = currentMillis;
          unlockDoor(exitDoor);
          systemState = 4;
          Serial.println("Puerta de salida abierta por 10 segundos");
          break;
        }
      }
    }

    // Manejar cierre de puerta
    if (systemState == 4 && (currentMillis - exitMillis >= EXIT_UNLOCK_TIME)) {
      lockDoor(exitDoor);
      systemState = 0;
      
      // Actualizar contador solo si el cajón sigue libre
      if (currentExitIndex != -1 && !digitalRead(dipPines[currentExitIndex])) {
        espaciosDisponibles++;
        Serial.print("Espacio ");
        Serial.print(currentExitIndex + 1);
        Serial.println(" confirmado como libre");
      }
      
      currentExitIndex = -1;
      procesandoSalida = false;
      Serial.println("Puerta de salida cerrada");
    }
  }


  void sendToServer() {
    if (!client.connect("192.168.43.31", 5000)) {  // ¡CAMBIAR POR TU IP!
      Serial.println("Error conectando al servidor");
      return;
    }

    // Crear JSON con formato seguro
    char jsonBuffer[128];  // Tamaño calculado: {"spaces":3,"rfid":"13 80 89 1A","entrance":90,"exit":0,"cajones":[0,1,0]} → 72 caracteres
    snprintf(jsonBuffer, sizeof(jsonBuffer),
            "{\"spaces\":%d,\"rfid\":\"%s\",\"entrance\":%d,\"exit\":%d,\"cajones\":[%d,%d,%d]}",
            espaciosDisponibles,
            lastRFID,
            entranceDoor.read(),
            exitDoor.read(),
            digitalRead(dipPines[0]),  // Cajón 1 (pin 13)
            digitalRead(dipPines[1]),  // Cajón 2 (pin 32)
            digitalRead(dipPines[2])   // Cajón 3 (pin 35)
    );

    client.println(jsonBuffer);
    client.stop();

    memset(lastRFID, 0, sizeof(lastRFID));  // Resetear RFID después del envío
  }

  void actualizarCajones(unsigned long currentMillis) {
    static unsigned long lastUpdate = 0;
    static bool estadosPrevios[NUM_CAJONES] = { true, true, true };

    if (currentMillis - lastUpdate >= 100) {
      lastUpdate = currentMillis;
      espaciosDisponibles = 0;

      for (int i = 0; i < NUM_CAJONES; i++) {
        bool estadoActual = digitalRead(dipPines[i]);

        // Detectar flanco de bajada (ocupado -> libre)
        if (estadosPrevios[i] && !estadoActual) {
          if (!exitTriggers[i] && !procesandoSalida) {
            exitTriggers[i] = true;  // Marcar trigger para este cajón
            Serial.print("¡Trigger de salida activado en cajón ");
            Serial.print(i + 1);
            Serial.println("!");
          }
        }
        estadosPrevios[i] = estadoActual;
        if (!estadoActual) espaciosDisponibles++;
      }
    }
  }

  void verificarLlenado(unsigned long currentMillis) {
    static unsigned long lastCheck = 0;
    static bool llenoAnterior = false;
    
    if (currentMillis - lastCheck >= 1000) {
      lastCheck = currentMillis;
      bool lleno = (espaciosDisponibles == 0);
      
      if (lleno && !llenoAnterior && !procesandoSalida) { // Ignorar si hay salida en proceso
        Serial.println("ALERTA: Estacionamiento lleno");
        if (systemState == 1 || systemState == 3) {
          digitalWrite(21, LOW);
          lockDoor(entranceDoor);
          systemState = 0;
        }
      }
      llenoAnterior = lleno;
    }
  }

  // Control de servomotores
  void unlockDoor(Servo& door) {
    door.write(90);
    Serial.println(door.attached() == ENTRANCE_SERVO_PIN ? "Entrada abierta" : "Salida abierta");
  }

  void lockDoor(Servo& door) {
    door.write(0);
    Serial.println(door.attached() == ENTRANCE_SERVO_PIN ? "Entrada cerrada" : "Salida cerrada");
  }

  void lockAllDoors() {
    lockDoor(entranceDoor);
    lockDoor(exitDoor);
  }