//potential error in code: 
//no 'in' command reading that gui sends
//'plot' is never sent by gui
//'float' command tells the float to mount
//no conditions for when 'mount' command is sent by gui


#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <MS5837.h>
#include <Stepper.h>
#include <Wire.h>
//above imports important libraries

MS5837 sensor;
const int stepsPerRevolution = 5000;  
const int dirPin = 6;  
const int stepPin = 5; 
const int enablePin = 13; 
const int stepReps = 6; 

Stepper myStepper(stepsPerRevolution, dirPin, stepPin);

const char* ssid = "TP-LINK_643A";  //wifi name   
const char* password = "78845558"; //wifi password
float pressure = 0.0;
float depth = 0.0;
const float pressureThreshold = 1307.55;  // estimated
bool mounted = false;

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
  //above code is the setup code for the ardruino and the pins

  if (!sensor.init()) {//if sensor doesnt initalize for some reason
    Serial.println("Sensor init failed!");
    while(1);  
  }
  sensor.setModel(MS5837::MS5837_30BA);
  sensor.setFluidDensity(1020); // density for freshwater

  // Connect to WiFi network
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {//tries to connect with wifi
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  server.begin(); // Start the server

  lastDataPointTime = 0; // Initialize the timer for data collection


}

void loop() {//code that constantly loops
  // Check if a client has connected
  WiFiClient client = server.available();
  if (!client) {
    return; // No client connected, skip the rest of the loop
  }

  // Wait for data from client
  while(!client.available()){
    delay(1);
  }

  String request = client.readStringUntil('\n');
  request.trim(); // Remove any newline characters
  if (request.equals("plot")) {//checks if gui sent the 'plot' command to ardruino
        client.println(logData());//prints the data based on logData method
  }
  if (request.equals("float")) {//checks if gui sent the 'float' command to ardruino

    if (!mounted) {//mounts the float first
      // floating set up
      digitalWrite(enablePin, LOW);

      digitalWrite(dirPin, LOW);
      for (int i =0 ; i < 2 ; i++) {
        digitalWrite(D3, LOW);
          // Spin motor quickly
          for (int i = 0; i < stepReps/2; i++) {
            for(int x = 0; x < stepsPerRevolution; x++)
            {
              digitalWrite(stepPin, HIGH);
              delayMicroseconds(1000);
              digitalWrite(stepPin, LOW);
              delayMicroseconds(1000);
            }
            delay(500);
          }
      }
      mounted = true;
      
      digitalWrite(enablePin, HIGH);

    }
    startingTime = millis();
    lastDataPointTime = startingTime;
    updateSensors();
    client.println("Time: 0, Pressure: " + String(pressure) + ", Depth: " + String(depth));
        
    dataPoints[dataPointIndex++] = {0, depth, pressure};

    Stall(8000);
    // Execute the float operation

    FloatDown();
    FloatUp();  
    digitalWrite(enablePin, HIGH);
    reconnectToWiFi();


    // Stall(10000);
    // Send data back to client
  }
  
}

void reconnectToWiFi() {
    WiFi.disconnect();
    Stall(5000);
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Reconnecting to WiFi...");
        WiFi.begin(ssid, password);
        while (WiFi.status() != WL_CONNECTED) {
            Stall(500);
            Serial.print(".");
        }
        Serial.println("WiFi connected");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    }
    Serial.println("DONE!");
}

void FloatDown() {
  // initial push out first

  digitalWrite(dirPin, HIGH);

  for (int i =0; i < 2; i++) {
    digitalWrite(enablePin, LOW);

    digitalWrite(D3, LOW);

    // Spin motor quickly
    for (int i = 0; i < stepReps/2; i++) {
      for(int x = 0; x < stepsPerRevolution; x++)
      {
        digitalWrite(stepPin, HIGH);
        delayMicroseconds(1000); // Short delays for stepping are okay
        digitalWrite(stepPin, LOW);
        delayMicroseconds(1000); // Short delays for stepping are okay
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
    sensor.setFluidDensity(1020); // density for freshwater
    Stall(5000); // Replace delay(20000) with Stall(20000), adjust time as needed
  }
}


void Stall(int stallAmt) {
  unsigned long start = millis()-startingTime;
  while(millis()-startingTime - start < stallAmt) {
    logDataPoint(); // Check if it's time to log a data point
    delay(50);
  }
}


void FloatUp() {

   digitalWrite(dirPin, LOW);
   for (int i =0 ; i < 2 ; i++) {
    digitalWrite(enablePin, LOW);
    digitalWrite(D3, LOW);
      // Spin motor quickly
      for (int i = 0; i < stepReps/2; i++) {
        for(int x = 0; x < stepsPerRevolution; x++)
        {
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
      sensor.setFluidDensity(1020); // density for freshwater
      Stall(5000); // Replace delay(20000) with Stall(20000), adjust time as needed
   }
}

String logData() {
  String dataPacket = ""; 

  // Append each data point, formatted as time:depth, separated by semicolons
  for (int i = 0; i < dataPointIndex; i++) {
    
    if (i > 0) dataPacket += ";"; // Add a delimiter between data points, but not before the first one

    if (i != dataPointIndex-1) {
      if (dataPoints[i+1].time == dataPoints[i].time) {
        continue;
      }
    }
    dataPacket += String(dataPoints[i].time) + ":" + String(dataPoints[i].depth) + ":" + String(dataPoints[i].pressure);
  }

  // Reset all data points to zero
  for (int i = 0; i < 100; i++) {
    dataPoints[i].time = 0;
    dataPoints[i].depth = 0.0;
    dataPoints[i].pressure = 0.0;
  }

  // Reset the index to start logging new data points at the beginning of the array
  dataPointIndex = 0;

  return dataPacket;
}

void logDataPoint() {
  unsigned long currentTime = millis();  // Time since start
  unsigned long nextDataPointTime = lastDataPointTime + 1000;  // Schedule the next data point time


  if (dataPointIndex < 100 && currentTime >= nextDataPointTime) {
    updateSensors(); // Update sensors to get the latest readings

    // Update lastDataPointTime for the next call (keeps it at 5-second intervals)
    lastDataPointTime = nextDataPointTime;

    // Calculate output time in seconds and adjust to be a multiple of 5
    unsigned long output = (currentTime / 1000)-startingTime/1000;

    // Store the new data point
    dataPoints[dataPointIndex++] = {output, depth, pressure};
    Serial.print("Logged at: ");
    Serial.print(output);
  }
}



void updateSensors() {
  sensor.read(); 
  pressure = sensor.pressure();  
  depth = sensor.depth()*1.33; 
  pressure *= 0.1 * 1.33;
}

float pressureToDepth(float pressure) {
  return (pressure - 1013.25) / 10.0;
}
