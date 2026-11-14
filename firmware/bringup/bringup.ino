// Supervised bench firmware only. No automatic watering or remote commands.
#include <Arduino.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <Preferences.h>
#include <esp_timer.h>
#include <driver/gpio.h>

constexpr int SOIL_PIN=34, LIGHT_PIN=35, DHT_PIN=27, FLOAT_PIN=26, RELAY_PIN=25;
constexpr bool RELAY_ACTIVE_LOW=false;
// Set true ONLY after verifying relay logic and reset/OFF with pump disconnected.
constexpr bool ENABLE_PUMP_TEST = false ;
constexpr int RELAY_OFF=RELAY_ACTIVE_LOW ? HIGH : LOW;
DHT dht(DHT_PIN,DHT22);
Preferences prefs;
esp_timer_handle_t cutoff=nullptr;
portMUX_TYPE pumpMux=portMUX_INITIALIZER_UNLOCKED;
bool pumping=false;
uint32_t lastStop=0, armUntil=0, lastSample=0, sequence=0;
int dry=-1, wet=-1, soilRaw=0, lightRaw=0;
float temperature=NAN, humidity=NAN;
bool storageReady=false, armed=false;
String line;
char bootId[20];

void stopPump(void*) {
  portENTER_CRITICAL(&pumpMux);
  gpio_set_level((gpio_num_t)RELAY_PIN,RELAY_OFF);
  pumping=false;
  lastStop=millis();
  portEXIT_CRITICAL(&pumpMux);
}
bool isPumping() {
  portENTER_CRITICAL(&pumpMux);
  bool result=pumping;
  portEXIT_CRITICAL(&pumpMux);
  return result;
}
int medianRead(int pin) {
  int v[15];
  for(int i=0;i<15;++i) v[i]=analogRead(pin);
  for(int i=1;i<15;++i) { int x=v[i],j=i-1; while(j>=0 && v[j]>x) {v[j+1]=v[j];--j;} v[j+1]=x; }
  return v[7];
}
bool calibrated() {return dry>50 && dry<4045 && wet>50 && wet<4045 && abs(dry-wet)>=200;}
bool rawOK() {return soilRaw>50 && soilRaw<4045;}
void sample() {
  soilRaw=medianRead(SOIL_PIN); lightRaw=medianRead(LIGHT_PIN);
  temperature=dht.readTemperature(); humidity=dht.readHumidity();
  lastSample=millis();
}
void printSample() {
  JsonDocument j;
  j["schema_version"]=1; j["build_stage"]="bench_bringup";
  j["device_id"]="garden-01"; j["boot_id"]=bootId;
  j["sample_seq"]=++sequence; j["uptime_ms"]=millis(); j["timestamp"]=nullptr;
  j["data_origin"]="real"; j["calibration_id"]=String("soil-")+dry+"-"+wet;
  j["soil_raw"]=soilRaw; j["soil_valid"]=rawOK() && calibrated();
  if(rawOK() && calibrated()) j["soil_pct"]=constrain(100.0f*(soilRaw-dry)/(wet-dry),0.0f,100.0f);
  else j["soil_pct"]=nullptr;
  bool airOK=isfinite(temperature) && isfinite(humidity) && humidity>=0 && humidity<=100;
  j["air_valid"]=airOK;
  if(airOK) {j["temperature_c"]=temperature;j["humidity_pct"]=humidity;}
  else {j["temperature_c"]=nullptr;j["humidity_pct"]=nullptr;}
  j["light_raw"]=lightRaw; j["light_lux"]=nullptr;
  j["tank_ok"]=digitalRead(FLOAT_PIN)==LOW;
  j["pump_on"]=isPumping();j["mode"]="BENCH";
  j["dry_raw"]=dry;j["wet_raw"]=wet;
  serializeJson(j,Serial);Serial.println();
}
void handle(String cmd) {
  cmd.trim();
  if(cmd=="stop") {armed=false;stopPump(nullptr);if(cutoff) esp_timer_stop(cutoff);Serial.println("# stopped");return;}
  if(cmd=="status") {printSample();return;}
  if(cmd=="help") {Serial.println("# status | dry | wet | arm | pump | stop; pump=1000ms, arm expires in 10s");return;}
  if(isPumping()) {Serial.println("# busy; use stop");return;}
  if(cmd=="dry" || cmd=="wet") {
    soilRaw=medianRead(SOIL_PIN);
    if(!storageReady || !rawOK()) {Serial.println("# calibration refused: storage/raw");return;}
    if(prefs.putInt(cmd.c_str(),soilRaw)!=sizeof(int32_t)) {Serial.println("# save failed");return;}
    if(cmd=="dry") dry=soilRaw;else wet=soilRaw;
    Serial.println("# saved reference; soil_pct valid only when both references span >=200 ADC counts");
    printSample();return;
  }
  if(cmd=="arm") {
    if(!ENABLE_PUMP_TEST || !cutoff) {Serial.println("# pump test disabled in source or timer unavailable");return;}
    armed=true;armUntil=millis()+10000;Serial.println("# armed for ONE pulse within 10s");return;
  }
  if(cmd=="pump") {
    bool authorized=armed && int32_t(armUntil-millis())>0;
    armed=false;
    if(!ENABLE_PUMP_TEST || !authorized || !cutoff || digitalRead(FLOAT_PIN)!=LOW) {
      Serial.println("# refused: enable/arm/tank/timer");return;
    }
    // No DHT/serial/network work while pumping. Timer callback also shuts off independently of loop.
    esp_timer_stop(cutoff);
    portENTER_CRITICAL(&pumpMux);
    bool cooled=uint32_t(millis()-lastStop)>=10000;
    if(cooled) {
      pumping=true;
      gpio_set_level((gpio_num_t)RELAY_PIN,!RELAY_OFF);
      if(esp_timer_start_once(cutoff,3000000)!=ESP_OK) {
        gpio_set_level((gpio_num_t)RELAY_PIN,RELAY_OFF);pumping=false;
      }
    }
    portEXIT_CRITICAL(&pumpMux);
    Serial.println(isPumping() ? "# pulse started: 3000ms" : "# refused: cooldown/timer");return;
  }
  if(cmd.length()) Serial.println("# unknown command; type help");
}
void setup() {
  digitalWrite(RELAY_PIN,RELAY_OFF);pinMode(RELAY_PIN,OUTPUT);
  pinMode(FLOAT_PIN,INPUT_PULLUP); // Closed to GND = enough water. Open/broken wire = empty.
  Serial.begin(115200);line.reserve(40);
  snprintf(bootId,sizeof(bootId),"%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random());
  analogReadResolution(12);analogSetPinAttenuation(SOIL_PIN,ADC_11db);analogSetPinAttenuation(LIGHT_PIN,ADC_11db);
  dht.begin();
  storageReady=prefs.begin("sg-bench",false);
  if(storageReady) {dry=prefs.getInt("dry",-1);wet=prefs.getInt("wet",-1);}
  esp_timer_create_args_t args={};args.callback=stopPump;args.name="pump-cutoff";
  if(esp_timer_create(&args,&cutoff)!=ESP_OK) cutoff=nullptr;
  lastStop=millis();
  Serial.println("# Smart-Green bench. Pump test disabled by default. Type help. JSON every 3s.");
}
void loop() {
  if(isPumping() && digitalRead(FLOAT_PIN)!=LOW) stopPump(nullptr);
  // Bound input work; oversized lines are discarded until newline, never executed as suffix commands.
  static bool discard=false;
  for(int i=0;i<32 && Serial.available();++i) {
    char c=Serial.read();
    if(c=='\n') {if(!discard) handle(line);line="";discard=false;}
    else if(c!='\r' && !discard) {if(line.length()<40) line+=c;else {discard=true;line="";}}
  }
  if(!isPumping() && uint32_t(millis()-lastSample)>=3000) {sample();printSample();}
  delay(2);
}
