#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <ESP32Servo.h>

#define SS_PIN 5
#define RST_PIN 17
#define SERVO_PIN 4

// Tiempos en milisegundos
#define RELAY_TIME 1000
#define UNLOCK_TIME 5000

MFRC522 mfrc522(SS_PIN, RST_PIN);
Servo doorLock;

// Variables para control de tiempos
unsigned long previousMillis = 0;
byte systemState = 0;  // 0: Idle, 1: Autorizado, 2: No autorizado

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  doorLock.attach(SERVO_PIN);
  
  pinMode(21, OUTPUT);  // Rele para acceso autorizado
  pinMode(22, OUTPUT);  // Rele para acceso denegado
  
  lockDoor();
  Serial.println("Sistema listo...");
}

void loop() {
  // Control de tiempos no bloqueante
  unsigned long currentMillis = millis();
  
  // Máquina de estados
  switch(systemState) {
    case 1:  // Acceso autorizado
      if (currentMillis - previousMillis >= RELAY_TIME) {
        digitalWrite(21, LOW);
        unlockDoor();
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
      
    case 3:  // Tiempo de puerta abierta
      if (currentMillis - previousMillis >= UNLOCK_TIME) {
        lockDoor();
        systemState = 0;
      }
      break;
      
    default:  // Estado idle
      checkRFID();
      break;
  }
}

void checkRFID() {
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) return;

  // Leer UID
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

void unlockDoor() {
  doorLock.write(90);
  Serial.println("Puerta desbloqueada");
}

void lockDoor() {
  doorLock.write(0);
  Serial.println("Puerta bloqueada");
}