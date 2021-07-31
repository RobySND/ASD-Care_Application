//-------Arduino Sketch for NodeMCU, SPEAKER, MPU9250--------//
#include <Wire.h>
#include <math.h>
#include <SoftwareSerial.h>
#include <DFPlayer_Mini_Mp3.h>
#include <LiquidCrystal_I2C.h>
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>


#define SELECT D0 
#define CONFIRM D5
#define T_SAMPLE 1000
#define N_SEND_DEFAULT 4 //numero di secondi da fare il send verso il cloud (buffer dim)
#define MAX_N_SAMPLE 4 //quanti sample salta prima di inviare al buffer

//Parametri di sensibilita'
float THRESHOLD = 1.5; //soglia modulo
int MAX_OVER_THRESHOLD = 2; //soglia durata

// Interfaccia schermo LCD
int conf=LOW, sel=LOW;

//Contatore per tenere conto di quante chiamate sono memorizzate in locale
int cnt_send = 0;
int cnt_sample = MAX_N_SAMPLE;

//Istanze oggetti globali
LiquidCrystal_I2C lcd(0x27,16,2); 
SoftwareSerial mySerial(D1, D2); // RX, TX// CHANGE the "0x27" ADRESS FOR YOUR SCREEN CONFIGURATION

// WiFi related classes
ESP8266WiFiMulti WiFiMulti; // It Will handle the connection to the AccessPoint
HTTPClient http; // Client with respect to the Heroku-hosted server
WiFiClientSecure client; // Necessary for dealing with the HTTPS Protocol

// MPU9250 Slave Device Address
const uint8_t MPU9250SlaveAddress = 0x68;

// Select SDA and SCL pins for I2C communication 
const uint8_t scl = D6;
const uint8_t sda = D7;

// sensitivity scale factor respective to full scale setting provided in datasheet 
const uint16_t AccelScaleFactor = 16384;
const uint16_t GyroScaleFactor = 131;

// MPU9250 few configuration register addresses
const uint8_t MPU9250_REGISTER_SMPLRT_DIV   =  0x19;
const uint8_t MPU9250_REGISTER_USER_CTRL    =  0x6A;
const uint8_t MPU9250_REGISTER_PWR_MGMT_1   =  0x6B;
const uint8_t MPU9250_REGISTER_PWR_MGMT_2   =  0x6C;
const uint8_t MPU9250_REGISTER_CONFIG       =  0x1A;
const uint8_t MPU9250_REGISTER_GYRO_CONFIG  =  0x1B;
const uint8_t MPU9250_REGISTER_ACCEL_CONFIG =  0x1C;
const uint8_t MPU9250_REGISTER_FIFO_EN      =  0x23;
const uint8_t MPU9250_REGISTER_INT_ENABLE   =  0x38;
const uint8_t MPU9250_REGISTER_ACCEL_XOUT_H =  0x3B;
const uint8_t MPU9250_REGISTER_SIGNAL_PATH_RESET  = 0x68;

int16_t AccelX, AccelY, AccelZ, Temperature, GyroX, GyroY, GyroZ;
int cnt=0, number_song=0;

// Connection related parameters
const char* SSID_HOME = "illyaad";    
const char* PASSWORD_HOME = "1982Gonzo";
String HOST = "asd-care-server.herokuapp.com"; // HEROKU-hosted server

// Access key
const char* USER_ID = "134892235";//ila:"366589975"; rob:"46810939"; danjo:"134892235"; //User code required for accessing the provided services 

// Required URL for HTTP requests
String URL = "https://" + HOST + "/user?ID=" + String(USER_ID);

// Flags used by the GET and POST method requests
bool good_GET;
bool good_POST;



void setup() {
    //-------SETUP LCD---------//
  Serial.begin(9600);
  Wire.begin(D4,D3); // SCL > D3 | SDA > D4
  lcd.init();                      // initialize the lcd
  lcd.clear();
  lcd.backlight();
  lcd.setCursor(0, 0);

  
  //---------SETUP BUTTON----------//
  pinMode(SELECT, INPUT);
  pinMode(CONFIRM, INPUT);
  conf=LOW;
  sel=LOW;
  number_song=choose_song();
  Serial.print("numero canzone "); Serial.print(number_song); Serial.print("\n"); 

  
  //------SETUP MPU9250-------//
  Wire.begin(sda, scl);
  MPU9250_Init();

  
  //------SETUP DFPLAYER WITH SPEAKER-------//
  mySerial.begin (9600);
  mp3_set_serial (mySerial);  //set softwareSerial for DFPlayer-mini mp3 module 
  delay(1);  //wait 1ms for mp3 module to set volume
  mp3_set_volume (10);


  //------SETUP OF CONNECTION TO AP-------//
  wifi_setup_function();

}

void loop() {
  
  int next=1;
  double Ax, Ay, Az, T, Gx, Gy, Gz, modulo;
  
  if(digitalRead(SELECT)){
      while(digitalRead(SELECT));
      setup();
    }
      
  Read_RawValue(MPU9250SlaveAddress, MPU9250_REGISTER_ACCEL_XOUT_H);
  
  //divide each with their sensitivity scale factor
  Ax = (double)AccelX/AccelScaleFactor;
  Ay = (double)AccelY/AccelScaleFactor;
  Az = (double)AccelZ/AccelScaleFactor;


  modulo=sqrt(pow(Ax,2)+pow(Ay,2)+pow(Az,2));
  Serial.print("modulo: "); Serial.print(modulo); Serial.print("\n");
  if(modulo>=THRESHOLD){
    // Restore flag 1 and try to POST until the tutor has been notified properly
    collect_send(modulo, Ax, Ay, Az, 1);
    cnt=cnt+1; 
    if (cnt>=MAX_OVER_THRESHOLD){
      Serial.print("ATTENZIONE!!!"); Serial.print("\n");
      
      // Restore flag 2 and try to POST until the tutor has been notified properly
      collect_send(modulo, Ax, Ay, Az, 2);

      if(number_song!=1){
        while(next<number_song){
          mp3_next ();
          delay(100);
          next=next+1;
        }
        
        Serial.print("PLAY SONG\n");
        delay (10000);
        while(next>1){
              mp3_prev ();
              delay(100);
              next=next-1;
        }
        delay(100);
        mp3_stop();
        Serial.print("STOP MUSIC\n");
        delay (100);
      }
      else{
        mp3_play();
        Serial.print("PLAY SONG\n");
        delay (10000);
        mp3_stop();
        Serial.print("STOP MUSIC\n");
        delay (100);
        }
      
      
      cnt=0;
    }
  }
  else 
    cnt=0;
    collect_send(modulo, Ax, Ay, Az, 0);

  delay(T_SAMPLE);
}


//-------------------------- UTILITY FUNCTIONS --------------------------------------//


int choose_song(){
  int n_songs = 5;
  int song_i=1;
  int state=0;

  lcd.setCursor(0,0);
  lcd.clear();
  lcd.print("Scegli il brano ");
  lcd.setCursor(0,1);
  lcd.print("da riprodurre ");
  delay(1000);

  while(state!=2){
    //state 0: choose the song
    while(state==0){
      delay(100);
      lcd.setCursor(0,0);
      lcd.clear();
      //set cursor
      lcd.print("Brano ");lcd.print(song_i);
      //da mettere nella seconda riga
      lcd.setCursor(0,1);
      lcd.print("sx:OK, dx:NEXT");

      if(digitalRead(CONFIRM)){
        state=1;
      }
      if(digitalRead(SELECT)){
        if(song_i>=n_songs){
          song_i=1;
        }
        else{
          song_i=song_i+1;
        }
      }
    }

    // state 1: confirm?
    while(state==1){
      delay(100);
      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Confermi brano ");lcd.print(song_i);lcd.print("?");
      lcd.setCursor(0,1);
      lcd.print("sx:OK, dx:BACK");

      if(digitalRead(CONFIRM)){
        state=2;
      }
      if(digitalRead(SELECT)){
        state=0;
      }
    }
    delay(100);
  }
  delay(100);
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("Brano ");lcd.print(song_i);
  lcd.setCursor(0,1);
  lcd.print(" impostato!");
  delay(2000);
  lcd.clear();
  return song_i;
}


//-------------------------- WIFI SETUP --------------------------------------//

void wifi_setup_function(){
  // Wireless connection will be used in client mode only.
  WiFi.mode(WIFI_STA);
  // Add the information regarding the AP authentication keys
  WiFiMulti.addAP(SSID_HOME, PASSWORD_HOME);

  // Start connection with .run and wait till it has correctly been established
  while((WiFiMulti.run() != WL_CONNECTED)) {
    Serial.println("Sto provando a connettermi...\n");
    delay(1000);
  }
  // WARNING: Connection has been established
  Serial.println("Connessione all'AccessPoint effettuata con successo!\n");

  // WARNING: Starting connection to Web Application
  Serial.print("Mi sto connettendo ad ");
  Serial.print(HOST);
  Serial.println();

  //Fix per l'HTTPS
  client.setInsecure();
  client.connect(URL,443);
  
  // Fetch dei parametri di configurazionet
  connect_to_host(1);
  // Connection to Host
  connect_to_host(0);
  
}

String splitString(String str, char sep, int index)
{
 int found = 0;
 int strIdx[] = { 0, -1 };
 int maxIdx = str.length() - 1;

 for (int i = 0; i <= maxIdx && found <= index; i++)
 {
    if (str.charAt(i) == sep || i == maxIdx)
    {
      found++;
      strIdx[0] = strIdx[1] + 1;
      strIdx[1] = (i == maxIdx) ? i+1 : i;
    }
 }
 return found > index ? str.substring(strIdx[0], strIdx[1]) : "";
}

void connect_to_host(int select_if_config){
  
  String payload;
  http.addHeader("Content-Type", "application/x-www-urlencoded");

  //Start connection to server
  //NodeMCU_Client.begin(URL, root_ca);
  
  Serial.println("Connessione riuscita!");
  if(select_if_config==1){
    Serial.println("Fetch parametri");
    while(!http.begin(client, URL+"&CONFIG=1")) {
      Serial.println("Connessione non riuscita in configurazione!\nRiprovo...");
      delay(2000);
    }
    good_GET = false;
    while(good_GET == false){
      Serial.println("Recupero i parametri di configurazione...");
      payload = get_method();
      delay(2000);
    }
    THRESHOLD = splitString(payload, ',', 0).toFloat();
    MAX_OVER_THRESHOLD = splitString(payload, ',', 1).toInt();
    Serial.print("La soglia modulo è: "); Serial.print(THRESHOLD);  Serial.print("\n"); Serial.print("La soglia durata è: "); Serial.print(MAX_OVER_THRESHOLD); Serial.print("\n");
  }
  else {
//    Serial.println("Routine check");
    while(!http.begin(client, URL+"&CONFIG=0")) {
      Serial.println("Connessione non riuscita!Riprovo...");
      delay(500);
    }
//    Serial.println("Routine OK\n");
  }
  delay(500);

}



//-------------------------- WIFI DATA EXCHANGE METHODS --------------------------------------//

String timestamp_list = "[\"";
String acclerazione_list = "[\"";
String alert_list = "[\"";
String asse_x_list ="[\"";
String asse_y_list = "[\"";
String asse_z_list = "[\"";


void check_send(String payload, double accelerazione, double asse_x, double asse_y, double asse_z, int alert, int vector){
  
  connect_to_host(0);
  http.addHeader("Content-Type", "application/json");
  good_POST = false;
  while(good_POST == false){
    post_method(payload, accelerazione, asse_x, asse_y, asse_z, alert, vector); //1 to post vector
  }  
}

void collect_send(double accelerazione, double asse_x, double asse_y, double asse_z, int alert){
  //When user is recognized, he gets allowed to POST
  String payload;
  
  if(alert == 2){ //POST IMMEDIATELY
    good_GET = false;
    while(good_GET == false){
      payload = get_method(); //payload conterra' il timestamp
      delay(100);
    }  
    Serial.print("ALERT 2 CHECK SEND");
    check_send(payload, accelerazione, asse_x, asse_y, asse_z, alert, 0); //0 to post scalar
  }
  
  if(alert == 1){
    good_GET = false;
    while(good_GET == false){
      payload = get_method(); //payload conterra' il timestamp
      delay(100);
    } 
    timestamp_list += payload + "\"";
    acclerazione_list += String(accelerazione) + "\"";
    alert_list += String(alert) + "\"";
    asse_x_list += String(asse_x) + "\"";
    asse_y_list += String(asse_y) + "\"";
    asse_z_list += String(asse_z) + "\"";

    cnt_sample=MAX_N_SAMPLE;
    if(cnt_send >= N_SEND_DEFAULT){
      
      timestamp_list += ']';
      acclerazione_list += ']';
      alert_list += ']';
      asse_x_list += ']';
      asse_y_list += ']';
      asse_z_list += ']';
      
      Serial.print("ALERT 1 CHECK SEND");
      check_send(payload, accelerazione, asse_x, asse_y, asse_z, alert, 1); //1 to post vector

      //INVIO TUTTO
  
      timestamp_list = "[\"";
      acclerazione_list = "[\"";
      alert_list = "[\"";
      asse_x_list = "[\"";
      asse_y_list = "[\"";
      asse_z_list = "[\"";
      cnt_send = 0;
    }
    else{
      timestamp_list += ",\"";
      acclerazione_list += ",\"";
      alert_list += ",\"";
      asse_x_list += ",\"";
      asse_y_list += ",\"";
      asse_z_list += ",\"";
    }
  }
  
  if(alert == 0){ //APPEND AND IF FULL THEN POST
    if(cnt_sample >= MAX_N_SAMPLE){
      good_GET = false;
      while(good_GET == false){
        payload = get_method(); //payload conterra' il timestamp
        delay(100);
      } 
      timestamp_list += payload + "\"";
      acclerazione_list += String(accelerazione) + "\"";
      alert_list += String(alert) + "\"";
      asse_x_list += String(asse_x) + "\"";
      asse_y_list += String(asse_y) + "\"";
      asse_z_list += String(asse_z) + "\"";
  
      if(cnt_send >= N_SEND_DEFAULT){        
        timestamp_list += ']';
        acclerazione_list += ']';
        alert_list += ']';
        asse_x_list += ']';
        asse_y_list += ']';
        asse_z_list += ']';
        
        check_send(payload, accelerazione, asse_x, asse_y, asse_z, alert, 1); //1 to post vector
  
        //INVIO TUTTO
    
        timestamp_list = "[\"";
        acclerazione_list = "[\"";
        alert_list = "[\"";
        asse_x_list = "[\"";
        asse_y_list = "[\"";
        asse_z_list = "[\"";
        cnt_send = 0;
      }
      else{
        timestamp_list += ",\"";
        acclerazione_list += ",\"";
        alert_list += ",\"";
        asse_x_list += ",\"";
        asse_y_list += ",\"";
        asse_z_list += ",\"";
        cnt_send++;
      }
      cnt_sample=0;
    }
    else{    
      cnt_sample++;
    }
  }
}

String get_method() {
  //GET Preparation and sending
  //La connessione al server e' riuscita, quindi posso mandare una richiesta
  http.addHeader("Content-Type", "application/x-www-urlencoded");

  Serial.print("\nInoltro la richiesta GET\n");
  int codice_http_restituito_GET = http.GET();
  Serial.println("\nHo mandato una richiesta!\n");

  if(codice_http_restituito_GET > 0){ //If 200, request has been processed correctly, HTTP_CODE_OK
    Serial.printf("\nHTTP GET... codice %d\n", codice_http_restituito_GET);

    if( (codice_http_restituito_GET == HTTP_CODE_OK) || (codice_http_restituito_GET == HTTP_CODE_MOVED_PERMANENTLY) ){
      good_GET = true;
      String payload = http.getString();
      return payload;
    }
    good_GET = false;
  }
  else { //HTTP Request error: GET didn't get properly handled by the server
    Serial.printf("\nHTTP GET... ERRORE: %s\n", http.errorToString(codice_http_restituito_GET).c_str());
    good_GET = false;
    return "";
  }
}

void post_method(String payload, double accelerazione, double asse_x, double asse_y, double asse_z, int alert, int scalar_or_vector){
  //When user is recognized, he gets allowed to POST
  String pacchetto;
  http.addHeader("Content-Type", "application/json");
  int codice_http_restituito_POST;

//  Serial.print("\nInoltro la richiesta POST\n");
//  Serial.print(payload); Serial.println(timestamp_list);
  if(scalar_or_vector == 0){ //scalar
    pacchetto =
    "{\"user_ID\":\"" + String(USER_ID)
    + "\",\"Timestamp\":[\"" + String(payload)
    + "\"],\"Acceleration\":[\"" + String(accelerazione)
    + "\"],\"Ax\":[\"" + String(asse_x)
    + "\"],\"Ay\":[\"" + String(asse_y)
    + "\"],\"Az\":[\"" + String(asse_z)
    + "\"],\"Alarm\":[\"" + String(alert)
    + "\"]}";
//    Serial.print(pacchetto);
    codice_http_restituito_POST = http.POST(pacchetto);
  }
  else{
    pacchetto =
    "{\"user_ID\":\""+ String(USER_ID)
    + "\",\"Timestamp\":" + timestamp_list
    + ",\"Acceleration\":" + acclerazione_list
    + ",\"Ax\":" + asse_x_list
    + ",\"Ay\":" + asse_y_list
    + ",\"Az\":" + asse_y_list
    + ",\"Alarm\":" + alert_list
    + "}";
//    Serial.print(pacchetto); 
    codice_http_restituito_POST = http.POST(pacchetto);
  }

//  Serial.print("\nFINE POST\n");
  if(codice_http_restituito_POST > 0){
    good_POST = true;
    Serial.printf("\nHTTP POST... codice %d\n", codice_http_restituito_POST);
  }
  else {
      Serial.printf("\nHTTP POST... ERRORE: %s\n", http.errorToString(codice_http_restituito_POST).c_str());
  }

}



//-------------------------- MPU --------------------------------------//



void I2C_Write(uint8_t deviceAddress, uint8_t regAddress, uint8_t data){
  Wire.beginTransmission(deviceAddress);
  Wire.write(regAddress);
  Wire.write(data);
  Wire.endTransmission();
}

// read all 14 register
void Read_RawValue(uint8_t deviceAddress, uint8_t regAddress){
  Wire.beginTransmission(deviceAddress);
  Wire.write(regAddress);
  Wire.endTransmission();
  Wire.requestFrom(deviceAddress, (uint8_t)14);
  AccelX = (((int16_t)Wire.read()<<8) | Wire.read());
  AccelY = (((int16_t)Wire.read()<<8) | Wire.read());
  AccelZ = (((int16_t)Wire.read()<<8) | Wire.read());
}

//configure MPU9250
void MPU9250_Init(){
  delay(150);
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_SMPLRT_DIV, 0x07);
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_PWR_MGMT_1, 0x01);
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_PWR_MGMT_2, 0x00);
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_CONFIG, 0x00);
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_GYRO_CONFIG, 0x00);//set +/-250 degree/second full scale
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_ACCEL_CONFIG, 0x00);// set +/- 2g full scale
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_FIFO_EN, 0x00);
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_INT_ENABLE, 0x01);
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_SIGNAL_PATH_RESET, 0x00);
  I2C_Write(MPU9250SlaveAddress, MPU9250_REGISTER_USER_CTRL, 0x00);
}
