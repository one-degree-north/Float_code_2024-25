#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <MS5837.h>
#include <Stepper.h>
#include <Wire.h>

MS5837 sensor;
const int stepsPerRevolution = 5000;  
const int dirPin = 6;  
const int stepPin = 5; 
const int enablePin = 13; 
const int stepReps = 6; 

Stepper myStepper(stepsPerRevolution, dirPin, stepPin);

const char* ssid = "TP-LINK_643A";  
const char* password = "78845558"; 
float pressure = 0.0;
float depth = 0.0;
const float pressureThreshold = 1307.55;  // estimated
bool mounted = false;

// For depth maintenance
const float targetDepth = 2.5; // Target depth in meters
const float depthTolerance = 0.5; // +/- 50cm as allowed by competition

WiFiServer server(80); // TCP server on port 80

struct DataPoint {
  long time;
  float depth;
  float pressure;
};

DataPoint dataPoints[100];
int dataPointIndex = 0;
unsigned long lastDataPointTime = 0;
unsigned long startingTime = 0;

void setup() {
  Serial.begin(9600);
  Wire.begin(4, 5);

  pinMode(enablePin, OUTPUT); 
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);

  digitalWrite(enablePin, HIGH);

  if (!sensor.init()) {
    Serial.println("Sensor init failed!");
    while(1);  
  }
  sensor.setModel(MS5837::MS5837_30BA);
  sensor.setFluidDensity(1000); // Using 1000 for freshwater (competition pool)

  // Connect to WiFi network
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  server.begin(); // Start the server
  lastDataPointTime = 0;
}

void loop() {
  // Check if a client has connected
  WiFiClient client = server.available();
  if (!client) {
    return; // No client connected, skip the rest of the loop
  }

  // Wait for data from client with timeout
  unsigned long timeout = millis() + 3000; // 3 second timeout
  while(!client.available() && millis() < timeout){
    delay(10);
  }
  
  if (!client.available()) {
    client.stop();
    return;
  }

  String request = client.readStringUntil('\n');
  request.trim(); // Remove any newline characters
  
  Serial.print("Received command: ");
  Serial.println(request);

  if (request.equals("plot")) {
    // Send all logged data points to the client
    String dataPacket = logData();
    client.println(dataPacket);
    Serial.println("Sent data: " + dataPacket);
  }
  else if (request.equals("float")) {
    // Handle float command (includes mounting)
    if (!mounted) {
      MountFloat();
      mounted = true;
    }
    
    startingTime = millis();
    lastDataPointTime = startingTime;
    updateSensors();
    client.println("Time: 0, Pressure: " + String(pressure) + ", Depth: " + String(depth));
    
    dataPoints[dataPointIndex++] = {0, depth, pressure};

    Stall(8000);
    
    // Execute float operation
    FloatDown();
    MaintainDepth(targetDepth, 45); // Maintain 2.5m depth for 45 seconds
    FloatUp();
    
    digitalWrite(enablePin, HIGH);
    reconnectToWiFi();
  }
  else if (request.equals("in")) {
    // Added implementation for 'in' command
    if (mounted) {
      FloatUp(); // Make sure float comes back to surface
      digitalWrite(enablePin, HIGH);
      client.println("Float returned to surface");
      mounted = false;
    } else {
      client.println("Float is already in");
    }
  }
  else if (request.equals("mount")) {
    // Added implementation for 'mount' command
    if (!mounted) {
      MountFloat();
      mounted = true;
      client.println("Float mounted");
    } else {
      client.println("Float is already mounted");
    }
  }
  else {
    client.println("Unknown command");
  }
  
  client.stop();
}

void MountFloat() {
  // Mounting procedure
  digitalWrite(enablePin, LOW);
  digitalWrite(dirPin, LOW);
  
  for (int i = 0; i < 2; i++) {
    digitalWrite(D3, LOW);
    // Spin motor quickly
    for (int i = 0; i < stepReps/2; i++) {
      for(int x = 0; x < stepsPerRevolution; x++) {
        digitalWrite(stepPin, HIGH);
        delayMicroseconds(1000);
        digitalWrite(stepPin, LOW);
        delayMicroseconds(1000);
      }
      delay(500);
    }
  }
  
  digitalWrite(enablePin, HIGH);
}

void MaintainDepth(float targetDepth, int durationSeconds) {
  Serial.println("Maintaining depth at " + String(targetDepth) + "m for " + String(durationSeconds) + " seconds");
  
  unsigned long startTime = millis();
  unsigned long endTime = startTime + (durationSeconds * 1000);
  int successfulReadings = 0;
  
  while (millis() < endTime) {
    updateSensors();
    logDataPoint();
    
    // Check if we're at the target depth (with tolerance)
    if (abs(depth - targetDepth) <= depthTolerance) {
      // We're at the right depth, just wait
      successfulReadings++;
    } else {
      // Need to adjust depth
      if (depth < targetDepth - depthTolerance) {
        // Too shallow, need to go deeper
        AdjustDepth(false);
      } else if (depth > targetDepth + depthTolerance) {
        // Too deep, need to rise
        AdjustDepth(true);
      }
      
      // Reset successful readings count if we had to adjust
      successfulReadings = 0;
    }
    
    // Small delay between adjustments
    delay(200);
  }
  
  Serial.println("Depth maintenance complete");
}

void AdjustDepth(bool goUp) {
  // Quick adjustment of depth - small motor movements
  digitalWrite(enablePin, LOW);
  digitalWrite(dirPin, goUp ? LOW : HIGH);
  
  // Make a small adjustment
  for(int x = 0; x < stepsPerRevolution/10; x++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(1000);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(1000);
  }
  
  digitalWrite(enablePin, HIGH);
}

void reconnectToWiFi() {
  WiFi.disconnect();
  Stall(5000);
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Reconnecting to WiFi...");
    WiFi.begin(ssid, password);
    
    unsigned long timeout = millis() + 10000; // 10 second timeout
    while (WiFi.status() != WL_CONNECTED && millis() < timeout) {
      Stall(500);
      Serial.print(".");
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("WiFi connected");
      Serial.print("IP address: ");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println("WiFi connection failed!");
    }
  }
  Serial.println("DONE!");
}

void FloatDown() {
  Serial.println("Floating down...");
  digitalWrite(dirPin, HIGH);

  for (int i = 0; i < 2; i++) {
    digitalWrite(enablePin, LOW);
    digitalWrite(D3, LOW);

    // Spin motor quickly
    for (int i = 0; i < stepReps/2; i++) {
      for(int x = 0; x < stepsPerRevolution; x++) {
        digitalWrite(stepPin, HIGH);
        delayMicroseconds(1000);
        digitalWrite(stepPin, LOW);
        delayMicroseconds(1000);
      }
      delay(500);
    }
    digitalWrite(enablePin, HIGH);

    digitalWrite(D3, HIGH);

    Wire.begin();

    if (!sensor.init()) {
      Serial.println("Sensor init failed!");
      while(1);  
    }
    sensor.setModel(MS5837::MS5837_30BA);
    sensor.setFluidDensity(1000);
    Stall(5000);
  }
  
  Serial.println("Reached target depth");
}

void Stall(int stallAmt) {
  unsigned long start = millis() - startingTime;
  unsigned long targetEnd = start + stallAmt;
  
  while((millis() - startingTime) - start < stallAmt) {
    logDataPoint(); // Check if it's time to log a data point
    delay(50);
  }
}

void FloatUp() {
  Serial.println("Floating up...");
  digitalWrite(dirPin, LOW);
  
  for (int i = 0; i < 2; i++) {
    digitalWrite(enablePin, LOW);
    digitalWrite(D3, LOW);
    // Spin motor quickly
    for (int i = 0; i < stepReps/2; i++) {
      for(int x = 0; x < stepsPerRevolution; x++) {
        digitalWrite(stepPin, HIGH);
        delayMicroseconds(1000);
        digitalWrite(stepPin, LOW);
        delayMicroseconds(1000);
      }
      delay(500);
    }
    digitalWrite(enablePin, HIGH);

    digitalWrite(D3, HIGH);

    Wire.begin();

    if (!sensor.init()) {
      Serial.println("Sensor init failed!");
      while(1);  
    }
    sensor.setModel(MS5837::MS5837_30BA);
    sensor.setFluidDensity(1000);
    Stall(5000);
  }
  
  Serial.println("Returned to surface");
}

String logData() {
  String dataPacket = ""; 

  // Append each data point, formatted as time:depth:pressure, separated by semicolons
  for (int i = 0; i < dataPointIndex; i++) {
    if (i > 0) dataPacket += ";"; // Add a delimiter between data points
    
    // Skip duplicate time entries
    if (i != dataPointIndex-1) {
      if (dataPoints[i+1].time == dataPoints[i].time) {
        continue;
      }
    }
    
    dataPacket += String(dataPoints[i].time) + ":" + 
                 String(dataPoints[i].depth) + ":" + 
                 String(dataPoints[i].pressure);
  }

  // Reset data points array after sending
  dataPointIndex = 0;

  return dataPacket;
}

void logDataPoint() {
  unsigned long currentTime = millis();
  
  // We want to log data every 5 seconds as per competition requirements
  unsigned long nextDataPointTime = lastDataPointTime + 5000;  // 5 seconds

  if (dataPointIndex < 100 && currentTime >= nextDataPointTime) {
    updateSensors(); // Update sensors to get the latest readings
    lastDataPointTime = nextDataPointTime; // Update for next data point
    
    // Calculate output time in seconds
    unsigned long output = (currentTime - startingTime) / 1000;

    // Store the new data point
    dataPoints[dataPointIndex++] = {output, depth, pressure};
    Serial.print("Logged at: ");
    Serial.print(output);
    Serial.print("s, Depth: ");
    Serial.print(depth);
    Serial.print("m, Pressure: ");
    Serial.println(pressure);
  }
}

void updateSensors() {
  sensor.read(); 
  pressure = sensor.pressure();  
  depth = sensor.depth() * 1.33; // Apply calibration factor
  pressure *= 0.1 * 1.33; // Convert to kPa and apply calibration
}
