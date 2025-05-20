#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>
#include <EEPROM.h>

// Configuración DIP Switch y LEDs
#define NUM_CAJONES 4
const int dipPines[NUM_CAJONES] = {12, 13, 14, 15};  // Pines DIP switches
const int ledPines[NUM_CAJONES] = {16, 17, 18, 19};  // Pines LEDs

// Configuración RFID
#define SS_PIN 5
#define RST_PIN 17
MFRC522 mfrc522(SS_PIN, RST_PIN);

// Configuración Servomotores
#define ENTRANCE_SERVO_PIN 4
#define EXIT_SERVO_PIN 13
Servo entranceDoor;
Servo exitDoor;

// Configuración Infrarrojo
#define IR_PIN 25          // Pin del sensor IR
#define DETECTION_DELAY 500 // Tiempo anti-rebote

// Tiempos configurables
#define RELAY_TIME 1000         // Tiempo activación relay
#define UNLOCK_TIME 5000        // Tiempo puerta abierta

// Variables de control
unsigned long previousMillis = 0;
unsigned long exitMillis = 0;
byte systemState = 0;  // 0: Idle, 1: Autorizado (entrada), 2: Denegado (entrada), 3: Puerta abierta (entrada), 4: Salida activa
bool exitActive = false;
int espaciosDisponibles = 0;

void setup() {
  Serial.begin(9600);
  
  // Inicializar EEPROM
  EEPROM.begin(512);
  
  // Configurar pines DIP y LEDs
  for(int i = 0; i < NUM_CAJONES; i++) {
    pinMode(dipPines[i], INPUT_PULLDOWN);
    pinMode(ledPines[i], OUTPUT);
    digitalWrite(ledPines[i], EEPROM.read(i));
  }
  
  // Configurar RFID
  SPI.begin();
  mfrc522.PCD_Init();
  Serial.println("RFID inicializado");
  
  // Configurar servomotores
  entranceDoor.attach(ENTRANCE_SERVO_PIN);
  exitDoor.attach(EXIT_SERVO_PIN);
  lockAllDoors();
  
  // Configurar sensor IR
  pinMode(IR_PIN, INPUT);
  
  // Configurar relays
  pinMode(21, OUTPUT);  // Rele entrada
  pinMode(22, OUTPUT);  // Rele denegado
  
  Serial.println("Sistema de estacionamiento iniciado");
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Máquina de estados
  switch(systemState) {
    case 1:  // Acceso autorizado (entrada)
      if (currentMillis - previousMillis >= RELAY_TIME) {
        digitalWrite(21, LOW);
        unlockDoor(entranceDoor);
        previousMillis = currentMillis;
        systemState = 3;
      }
      break;
      
    case 2:  // Acceso denegado (entrada)
      if (currentMillis - previousMillis >= RELAY_TIME) {
        digitalWrite(22, LOW);
        systemState = 0;
      }
      break;
      
    case 3:  // Tiempo de puerta abierta (entrada)
      if (currentMillis - previousMillis >= UNLOCK_TIME) {
        lockDoor(entranceDoor);
        systemState = 0;
      }
      break;
      
    case 4:  // Salida activa
      if (currentMillis - exitMillis >= UNLOCK_TIME) {
        lockDoor(exitDoor);
        exitActive = false;
        systemState = 0;
        Serial.println("Puerta de salida cerrada");
      }
      break;
      
    default:  // Estado idle
      checkRFID();
      break;
  }

  // Control de salida con IR
  controlSalida(currentMillis);
  
  // Actualizar estado de cajones
  actualizarCajones(currentMillis);
  verificarLlenado(currentMillis);
}

// Control RFID
void checkRFID() {
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) return;

  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uid.concat(String(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " "));
    uid.concat(String(mfrc522.uid.uidByte[i], HEX));
  }
  uid.toUpperCase();

  Serial.print("UID detectado: ");
  Serial.println(uid);

  if (uid.substring(1) == "13 80 89 1A") {  // UID válido
    Serial.println("Acceso autorizado");
    digitalWrite(21, HIGH);
    previousMillis = millis();
    systemState = 1;
  } else {
    Serial.println("Acceso denegado");
    digitalWrite(22, HIGH);
    previousMillis = millis();
    systemState = 2;
  }
}

// Control de salida con IR
void controlSalida(unsigned long currentMillis) {
  static unsigned long lastDetection = 0;
  
  // Leer estado del sensor IR (LOW = objeto detectado)
  if (digitalRead(IR_PIN) == LOW && !exitActive) {
    if (currentMillis - lastDetection > DETECTION_DELAY) {
      unlockDoor(exitDoor);
      exitMillis = currentMillis;
      exitActive = true;
      systemState = 4;  // Cambiar a estado de salida activa
      Serial.println("Vehículo detectado en salida - Puerta abierta");
      lastDetection = currentMillis;
    }
  }
}

// Actualizar estado de cajones
void actualizarCajones(unsigned long currentMillis) {
  static unsigned long lastUpdate = 0;
  
  if (currentMillis - lastUpdate >= 100) {
    lastUpdate = currentMillis;
    espaciosDisponibles = 0; // Resetear contador
    
    for(int i = 0; i < NUM_CAJONES; i++) {
      bool estado = digitalRead(dipPines[i]);
      digitalWrite(ledPines[i], estado);
      if (!estado) espaciosDisponibles++; // Contar cajones libres
      
      if (estado != EEPROM.read(i)) {
        EEPROM.write(i, estado);
        EEPROM.commit();
      }
    }
  }
}

// Verificar si el estacionamiento está lleno
void verificarLlenado(unsigned long currentMillis) {
  static unsigned long lastCheck = 0;
  static bool llenoAnterior = false;
  
  if (currentMillis - lastCheck >= 1000) {
    lastCheck = currentMillis;
    bool lleno = (espaciosDisponibles == 0);
    
    if (lleno && !llenoAnterior) {
      Serial.println("ALERTA: Estacionamiento lleno");
    }
    llenoAnterior = lleno;
  }
}

// Control de servomotores
void unlockDoor(Servo &door) {
  door.write(90);
  Serial.println(door.attached() == ENTRANCE_SERVO_PIN ? "Entrada abierta" : "Salida abierta");
}

void lockDoor(Servo &door) {
  door.write(0);
  Serial.println(door.attached() == ENTRANCE_SERVO_PIN ? "Entrada cerrada" : "Salida cerrada");
}

void lockAllDoors() {
  lockDoor(entranceDoor);
  lockDoor(exitDoor);
}