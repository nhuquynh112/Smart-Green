#include "controller.h"
#include "sensor_math.h"
#include "pump_guard.h"
#include "protocol.h"
#include <cassert>
#include <iostream>
#include <string>
using namespace garden;
struct Pump : PumpOutput {
  bool on=false,allowed=true;unsigned starts=0;uint32_t measured=850;
  bool start(uint32_t) override {if(!allowed)return false;on=true;++starts;return true;}
  void off() override {on=false;}
  uint32_t actualDuration(uint32_t) override{return measured;}
};
struct Store : Storage {
  Pump* output=nullptr;State saved;bool ok=true,requireOff=false;
  bool save(const State& s) override {if(requireOff) assert(!output->on);saved=s;return ok;}
};
Config config(){Config c;c.commissioned=true;c.cooldownMs=1000;return c;}
Sensor sample(uint32_t ms){Sensor s;s.valid=true;s.tankOK=true;s.soil=20;s.sampledMs=ms;return s;}
Command water(uint32_t seq=1){Command c;c.kind=Command::Kind::Water;c.seq=seq;c.durationMs=1000;c.issuedAt=1800000000;c.expiresAt=1800000060;return c;}
JsonDocument validJson() {
  JsonDocument j;
  j["schema_version"]=1;j["device_id"]="garden-01";j["command_seq"]=1;j["kind"]="WATER";j["source"]="MANUAL";
  j["issued_at"]=1800000000LL;j["expires_at"]=1800000060LL;j["duration_ms"]=1000;
  return j;
}
int main(){
  constexpr int64_t utc=1800000001;
  assert(guardReason(1000,0,1000,1000,true)==Reason::Duration);
  assert(guardReason(999,0,1000,999,true)==Reason::Running);
  assert(guardReason(500,0,1000,500,false)==Reason::Tank);
  assert(guardReason(501,0,1000,0,true)==Reason::Guard);
  assert(guardReason(100,UINT32_MAX-499,600,100,true)==Reason::Duration);
  float pct=0;
  assert(!sensors::convert(2500,-1,-1,pct));assert(!sensors::convert(0,2800,1500,pct));
  assert(sensors::convert(2150,2800,1500,pct) && pct==50);
  assert(sensors::convert(2150,1500,2800,pct) && pct==50);
  assert(!sensors::convert(2000,2050,2000,pct));
  {Pump p;Store s;s.output=&p;s.requireOff=true;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0,&p);
   assert(std::string(c.command(water(),2000,utc,sample(2000)))=="started");assert(p.on);
   // OFF must occur before persisting the stop, including when storage fails.
   s.ok=false;c.tick(3000,utc+1,sample(3000));assert(!p.on && c.fault());}
  {Pump p;Store s;s.output=&p;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0,&p);
   c.command(water(),2000,utc,sample(2000));p.off();c.externalStop(2850,Reason::Duration);
   assert(!c.pumping());assert(c.state().events[0].actualMs==850);
   assert(c.state().events[0].reason==Reason::Duration);}
  {Pump p;Store s;State st;st.mode=Mode::Auto;Controller c(config(),st,s,0,&p);
   // No network calls at all: AUTO still runs after three fresh dry samples.
   c.tick(1000,utc,sample(1000));c.tick(2000,utc+1,sample(2000));c.tick(3000,utc+2,sample(3000));assert(p.on);
   c.externalStop(3500,Reason::Guard);assert(!p.on && c.fault());
   for(uint32_t t=4000;t<15000;t+=1000) {c.tick(t,utc+10,sample(t));}
   assert(p.starts==1);}
  {Pump p;Store s;State st;st.mode=Mode::Auto;Controller c(config(),st,s,0,&p);
   for(uint32_t t=1000;t<10000;t+=1000) {c.tick(t,0,sample(t));}
   assert(!p.on);}
  {Pump p;p.allowed=false;Store s;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0,&p);
   assert(std::string(c.command(water(),2000,utc,sample(2000)))=="output_fault");assert(!p.on && c.fault());}
  {Pump p;Store s;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0,&p);
   c.command(water(),2000,utc,sample(2000));c.tick(2100,utc,sample(0)); // still fresh at 2100
   Sensor stale=sample(0);c.tick(5000,utc+3,stale);assert(!p.on);
   assert(std::string(c.command(water(),6000,utc+4,sample(6000)))=="duplicate");}
  {Command c;auto j=validJson();assert(!protocol::parse(j,"garden-01",1000,c));assert(c.durationMs==1000);
   j["device_id"]="wrong";assert(protocol::parse(j,"garden-01",1000,c));}
  for(int i=0;i<11;++i) {
    auto j=validJson();Command c;
    switch(i) {
      case 0:j["command_seq"]=-1;break;case 1:j["command_seq"]=true;break;
      case 2:j["duration_ms"]="1000";break;case 3:j["duration_ms"]=1001;break;
      case 4:j["issued_at"]="1800000000";break;case 5:j["expires_at"]=INT64_MAX;break;
      case 6:j["source"]="RULE";break;case 7:j["kind"]="START";break;
      case 8:j["schema_version"]=true;break;case 9:j["duration_ms"]=0;break;
      case 10:j["kind"]="SET_MODE";j["mode"]="ON";break;
    }
    assert(protocol::parse(j,"garden-01",1000,c));
  }
  {auto j=validJson();j["kind"]="STOP";j["expires_at"]=1800000000LL;Command cmd;
   assert(!protocol::parse(j,"garden-01",1000,cmd));assert(cmd.kind==Command::Kind::Stop);}
  std::cout<<"runtime: sensor, protocol, physical output ordering and offline safety passed\n";
}
