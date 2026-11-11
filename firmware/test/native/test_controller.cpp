#include "controller.h"
#include <cassert>
#include <iostream>
using namespace garden;
struct Store : Storage { bool ok=true; State saved; bool save(const State& s) override { if(ok) saved=s; return ok; } };
Config config() { Config c; c.commissioned=true; c.cooldownMs=1000; return c; }
Sensor sample(uint32_t ms,float soil=20) { Sensor s; s.soil=soil;s.valid=true;s.tankOK=true;s.sampledMs=ms; return s; }
Command water(uint32_t seq=1) { Command c; c.kind=Command::Kind::Water;c.seq=seq;c.durationMs=2000;c.issuedAt=1800000000;c.expiresAt=1800000060;return c; }
int main() {
  const int64_t utc=1800000001;
  { Store s; State st; st.mode=Mode::Auto;Controller c(config(),st,s,0);
    Command stop;stop.kind=Command::Kind::Stop;stop.seq=1;stop.issuedAt=utc-100;stop.expiresAt=utc-50;
    c.command(stop,2000,utc,sample(2000));assert(c.mode()==Mode::Off);
    for(uint32_t t=3000;t<10000;t+=1000)c.tick(t,utc,sample(t));
    assert(!c.pumping() && s.saved.mode==Mode::Off);
    st.mode=Mode::Auto;Controller off(config(),st,s,0);
    stop.kind=Command::Kind::SetMode;stop.mode=Mode::Off;
    assert(std::string(off.command(stop,2000,0,sample(2000)))=="stopped");
    assert(off.mode()==Mode::Off);

  }
  { Store s; State st; st.mode=Mode::Manual; auto cfg=config();
    cfg.cooldownMs=600000;cfg.manualCooldownMs=0;assert(cfg.valid());
    Controller c(cfg,st,s,0);assert(c.cooldownRemaining(0)==0);
    assert(std::string(c.command(water(1),1,utc,sample(1)))=="started");
    c.tick(2001,utc+2,sample(2001));assert(!c.pumping());
    assert(std::string(c.command(water(2),2002,utc+2,sample(2002)))=="started");
    st.mode=Mode::Auto;Controller automatic(cfg,st,s,0);
    assert(automatic.cooldownRemaining(1)==599999);
  }
  { Store s; State st; st.mode=Mode::Manual; auto cfg=config();
    cfg.cooldownMs=600000;cfg.manualCooldownMs=180000;
    Controller c(cfg,st,s,0);
    assert(c.cooldownRemaining(179999)==1);
    assert(std::string(c.command(water(1),179999,utc,sample(179999)))=="cooldown");
    assert(std::string(c.command(water(2),180000,utc,sample(180000)))=="started");
    c.tick(182000,utc+2,sample(182000));
    assert(c.cooldownRemaining(182000)==180000);
    st.mode=Mode::Auto;Controller automatic(cfg,st,s,0);
    assert(automatic.cooldownRemaining(180000)==420000);
  }
  { Store s; State st; Controller c(config(),st,s,100);
    assert(c.cooldownRemaining(100)==1000);
    assert(c.cooldownRemaining(600)==500);
    assert(c.cooldownRemaining(1100)==0);
  }
  { Store s; State st; Controller c(config(),st,s,UINT32_MAX-499);
    assert(c.cooldownRemaining(0)==500);
    assert(c.cooldownRemaining(500)==0);
  }
  { Store s; State st; st.mode=Mode::Manual; Config cfg=config();cfg.commissioned=false;
    Controller c(cfg,st,s,0);c.command(water(),2000,utc,sample(2000));assert(!c.pumping()); }
  { Store s; State st;st.mode=Mode::Manual;Controller c(config(),st,s,0);
    assert(std::string(c.command(water(),2000,utc,sample(2000)))=="started");
    assert(s.saved.reservedMs==2000 && s.saved.events[0].reason==Reason::Running);
    c.tick(4000,utc+2,sample(4000));assert(!c.pumping());
    assert(c.state().events[0].reason==Reason::Duration);
    c.command(water(),6000,utc+4,sample(6000));assert(!c.pumping());
    Controller reboot(config(),s.saved,s,6000);
    reboot.command(water(),8000,utc+6,sample(8000));assert(!reboot.pumping()); }
  { Store s;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0);
    s.ok=false;c.command(water(),2000,utc,sample(2000));assert(!c.pumping() && c.fault()); }
  { Store s;State st;st.mode=Mode::Auto;Controller c(config(),st,s,0);
    c.tick(2000,utc,sample(2000));c.tick(2010,utc,sample(2000));assert(!c.pumping());
    c.tick(3000,utc+1,sample(3000));assert(!c.pumping());
    c.tick(4000,utc+2,sample(4000));assert(c.pumping());
    c.tick(4100,utc+2,sample(4100,50));assert(!c.pumping()); }
  for(int fault=0;fault<3;++fault) {
    Store s;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0);
    c.command(water(),2000,utc,sample(2000));auto v=sample(2100);
    if(fault==0) v.valid=false;
    if(fault==1) v.tankOK=false;
    if(fault==2) v.soil=NAN;
    c.tick(2100,utc,v);assert(!c.pumping());
  }
  { Store s;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0);
    auto w=water();w.expiresAt=utc;c.command(w,2000,utc,sample(2000));assert(!c.pumping());
    w=water();w.durationMs=999999;c.command(w,3000,utc,sample(3000));assert(!c.pumping()); }
  { Store s;State st;st.mode=Mode::Manual;st.starts=4;st.windowStart=utc;Controller c(config(),st,s,0);
    c.command(water(),2000,utc,sample(2000));assert(!c.pumping()); }
  { Store s;State st;st.mode=Mode::Manual;Controller c(config(),st,s,UINT32_MAX-3000);
    c.command(water(),UINT32_MAX-1000,utc,sample(UINT32_MAX-1000));assert(c.pumping());
    c.tick(1000,utc+2,sample(1000));assert(!c.pumping()); }
  { Store s;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0);
    c.command(water(),2000,utc,sample(2000));Controller reboot(config(),s.saved,s,0);
    assert(!reboot.pumping() && reboot.state().events[0].reason==Reason::Reboot);
    assert(reboot.state().reservedMs==2000);
    assert(reboot.acknowledgeEvent(1));assert(reboot.state().eventCount==0); }
  { Store s;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0);
    c.command(water(),2000,utc,sample(2000));Command stop;stop.kind=Command::Kind::Stop;
    c.command(stop,2100,utc,sample(2100));assert(!c.pumping()); }
  { Store s;State st;st.mode=Mode::Off;Controller c(config(),st,s,0);
    for(uint32_t t=1000;t<10000;t+=1000) { c.tick(t,utc,sample(t)); }
    assert(!c.pumping()); }
  { Store s;State st;st.mode=Mode::Manual;st.starts=20;st.windowStart=utc;
    auto cfg=config();cfg.manualUnlimitedStarts=true;Controller c(cfg,st,s,0);
    c.command(water(),2000,utc,sample(2000));assert(c.pumping()); }
  { Store s;State st;st.mode=Mode::Manual;st.starts=20;st.windowStart=utc;
    auto cfg=config();cfg.manualUnlimitedStarts=true;st.reservedMs=cfg.maxDayMs;Controller c(cfg,st,s,0);
    c.command(water(),2000,utc,sample(2000));assert(!c.pumping()); }
  { Store s;State st;st.mode=Mode::Auto;st.starts=20;st.windowStart=utc;
    auto cfg=config();cfg.manualUnlimitedStarts=true;Controller c(cfg,st,s,0);
    c.tick(2000,utc,sample(2000));c.tick(3000,utc+1,sample(3000));c.tick(4000,utc+2,sample(4000));assert(!c.pumping()); }
  { struct DelayedOutput:PumpOutput {
      bool on=false;bool start(uint32_t) override {on=true;return true;}
      void off() override {on=false;}
      uint32_t startedAt(uint32_t fallback) override {return fallback+40;}
    } output;
    Store s;State st;st.mode=Mode::Manual;Controller c(config(),st,s,0,&output);
    auto cmd=water();cmd.durationMs=500;c.command(cmd,2000,utc,sample(2000));
    c.tick(2040,utc,sample(2040));assert(output.on);
    c.tick(2500,utc,sample(2500));assert(output.on);
    c.tick(2540,utc,sample(2540));assert(!output.on);
    assert(c.state().events[0].actualMs==500);
  }
  std::cout<<"controller: all assertions passed\n";
}
