// Host audit only: no Arduino, GPIO, serial, network or real persistent storage.
#include "controller.h"
#include "pump_guard.h"
#include "command_delivery.h"
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <limits>
using namespace garden;
constexpr int64_t epoch=1800000000;
void require(bool ok) { if(!ok) throw std::runtime_error("expectation failed"); }
struct Output : PumpOutput {
  bool on=false, allowed=true; unsigned starts=0;
  bool start(uint32_t) override { if(!allowed)return false;on=true;++starts;return true; }
  void off() override {on=false;}
};
struct Store : Storage {
  State saved;bool ok=true;
  bool save(const State& s) override { if(ok)saved=s;return ok; }
};
Config config() {Config c;c.commissioned=true;c.cooldownMs=1000;c.pulseMs=1000;c.maxPulseMs=1000;
 c.maxDayMs=20000;c.maxDayStarts=20;c.separateManualQuota=true;c.manualUnlimitedStarts=true;c.manualCooldownMs=0;return c;}
State automatic(){State s;s.mode=Mode::Auto;return s;}
Sensor sample(uint32_t ms,float soil=20,bool tank=true,bool valid=true){return Sensor{soil,valid,tank,ms};}
struct Rig {
 Store store;Output out;Config cfg;Controller c;
 Rig(Config v=config(),State s=automatic()):cfg(v),c(v,s,store,0,&out){}
 void tick(uint32_t t,float soil=20,bool tank=true,bool valid=true,int64_t utc=epoch){c.tick(t,utc,sample(t,soil,tank,valid));}
 void dry(uint32_t t=1000){tick(t);tick(t+1000);tick(t+2000);}
};
Command command(Command::Kind kind,uint32_t seq=1,Mode mode=Mode::Off){Command c;c.kind=kind;c.seq=seq;c.mode=mode;c.issuedAt=epoch;c.expiresAt=epoch+60;return c;}
int main(){
 unsigned pass=0,fail=0;
 auto run=[&](const char* name,std::function<void()> f){try{f();++pass;std::cout<<"PASS | "<<name<<"\n";}catch(const std::exception& e){++fail;std::cout<<"FAIL | "<<name<<" | "<<e.what()<<"\n";}};
 run("A01 low boundary requires three distinct dry samples",[]{Rig r;r.tick(1000,30);r.tick(2000,30);require(!r.out.on);r.tick(3000,30);require(r.out.on&&r.out.starts==1);});
 run("A02 repeated same sample cannot satisfy debounce",[]{Rig r;for(int i=0;i<10;++i)r.c.tick(1000+i,epoch,sample(1000));require(!r.out.on);});
 run("A03 above low resets dry sequence",[]{Rig r;r.tick(1000);r.tick(2000);r.tick(3000,30.01f);r.tick(4000);r.tick(5000);require(!r.out.on);r.tick(6000);require(r.out.on);});
 run("A04 high boundary stops, intermediate moisture does not restart",[]{Rig r;r.dry();r.tick(3100,44.99f);require(r.out.on);r.tick(3200,45);require(!r.out.on&&r.c.state().events[0].reason==Reason::Wet);for(unsigned t=4000;t<10000;t+=1000)r.tick(t,40);require(r.out.starts==1);});
 run("A05 empty tank blocks AUTO",[]{Rig r;for(unsigned t=1000;t<10000;t+=1000)r.tick(t,20,false);require(!r.out.on&&r.c.state().eventCount==0);});
 run("A06 tank loss during AUTO stops and logs Tank",[]{Rig r;r.dry();r.tick(3100,20,false);require(!r.out.on&&r.c.state().events[0].reason==Reason::Tank);});
 run("A07 invalid soil flag blocks start and breaks debounce",[]{Rig r;r.tick(1000);r.tick(2000);r.tick(3000,20,true,false);r.tick(4000);r.tick(5000);require(!r.out.on);r.tick(6000);require(r.out.on);r.tick(6100,20,true,false);require(!r.out.on&&r.c.state().events[0].reason==Reason::Sensor);});
 run("A08 NaN infinity negative and over 100 soil block start",[]{for(float v:{NAN,INFINITY,-1.f,101.f}){Rig r;for(unsigned t=1000;t<10000;t+=1000)r.tick(t,v);require(!r.out.on);}});
 run("A09 stale soil blocks start and stops active pulse",[]{Rig r;for(unsigned t=5000;t<10000;t+=1000)r.c.tick(t,epoch,sample(0));require(!r.out.on);auto cfg=config();cfg.pulseMs=cfg.maxPulseMs=6000;Rig active(cfg);active.dry();active.c.tick(7001,epoch,sample(3000));require(!active.out.on&&active.c.state().events[0].reason==Reason::Sensor);});
 run("A10 stale boundary 4000ms valid, 4001ms rejected",[]{auto cfg=config();cfg.pulseMs=cfg.maxPulseMs=6000;Rig r(cfg);r.dry();r.c.tick(7000,epoch,sample(3000));require(r.out.on);r.c.tick(7001,epoch,sample(3000));require(!r.out.on);});
 run("A11 exact pulse duration and event reservation",[]{Rig r;r.dry();r.tick(3999);require(r.out.on);r.tick(4000);require(!r.out.on);auto e=r.c.state().events[0];require(e.reason==Reason::Duration&&e.actualMs==1000&&e.plannedMs==1000&&e.source==Source::Rule&&e.commandSeq==0&&r.c.state().reservedMs==1000);});
 run("A12 STOP OFF expired and duplicate shut down AUTO",[]{for(bool off:{false,true}){Rig r;r.dry();auto c=command(off?Command::Kind::SetMode:Command::Kind::Stop,0);c.issuedAt=epoch-100;c.expiresAt=epoch-50;r.c.command(c,3100,0,sample(3100));require(!r.out.on&&r.c.mode()==Mode::Off);r.dry(5000);require(r.out.starts==1&&r.c.state().events[0].reason==Reason::Stop);}});
 run("A13 OFF and MANUAL never run dry AUTO rule",[]{for(Mode m:{Mode::Off,Mode::Manual}){State s;s.mode=m;Rig r(config(),s);r.dry();require(!r.out.on);}});
 run("A14 AUTO cooldown not bypassed by zero manual cooldown",[]{Config c=config();c.cooldownMs=600000;Rig r(c);r.dry();require(!r.out.on);r.tick(599999);require(!r.out.on);r.tick(600000);require(r.out.on);r.tick(601000);require(!r.out.on);r.dry(602000);r.tick(1200999);require(!r.out.on);r.tick(1201000);require(r.out.on);});
 run("A15 AUTO count quota still enforced with unlimited manual starts",[]{auto s=automatic();s.windowStart=epoch;s.starts=20;Rig r(config(),s);r.dry();require(!r.out.on&&r.c.state().eventCount==0);});
 run("A16 insufficient time budget blocks full AUTO pulse",[]{auto s=automatic();s.windowStart=epoch;s.reservedMs=19500;Rig r(config(),s);r.dry();require(!r.out.on&&r.c.state().reservedMs==19500);});
 run("A17 exact remaining budget accepted, early stop no refund",[]{auto s=automatic();s.windowStart=epoch;s.reservedMs=19000;Rig r(config(),s);r.dry();require(r.out.on);r.tick(3100,45);require(r.c.state().reservedMs==20000);r.dry(5000);require(r.out.starts==1);});
 run("A18 AUTO and MANUAL budgets independent",[]{auto s=automatic();s.manualReservedMs=20000;s.manualStarts=40;s.manualWindowStart=epoch;Rig r(config(),s);r.dry();require(r.out.on&&r.c.state().manualReservedMs==20000&&r.c.state().reservedMs==1000);});
 run("A19 rolling 24h quota reset boundary",[]{auto s=automatic();s.windowStart=epoch;s.starts=20;s.reservedMs=20000;Rig r(config(),s);for(unsigned t=1000;t<=3000;t+=1000)r.tick(t,20,true,true,epoch+86399);require(!r.out.on);r.tick(4000,20,true,true,epoch+86400);require(r.out.on&&r.c.state().starts==1&&r.c.state().reservedMs==1000);});
 run("A20 missing clock and rollback block AUTO",[]{Rig r;for(unsigned t=1000;t<10000;t+=1000)r.tick(t,20,true,true,0);require(!r.out.on);auto s=automatic();s.lastWaterAt=epoch+10;Rig rollback(config(),s);rollback.dry();require(!rollback.out.on);});
 run("A21 commissioning invalid config and failed storage block start",[]{Config c=config();c.commissioned=false;Rig a(c);a.dry();require(!a.out.on);c=config();c.low=c.high;Rig b(c);b.dry();require(!b.out.on);Rig d;d.store.ok=false;d.dry();require(!d.out.on&&d.c.fault());});
 run("A22 failed output and guard latch fault prevent restart",[]{Rig r;r.out.allowed=false;r.dry();require(!r.out.on&&r.c.fault());r.out.allowed=true;r.dry(6000);require(r.out.starts==0);Rig g;g.dry();g.c.externalStop(3100,Reason::Guard);g.dry(6000);require(!g.out.on&&g.out.starts==1&&g.c.fault());});
 run("A23 full log blocks watering until FIFO ACK",[]{auto s=automatic();s.eventCount=32;s.nextEvent=33;for(unsigned i=0;i<32;++i){s.events[i].id=i+1;s.events[i].reason=Reason::Duration;}Rig r(config(),s);r.dry();require(!r.out.on&&!r.c.acknowledgeEvent(2));require(r.c.acknowledgeEvent(1));r.tick(4000);require(r.out.on&&r.c.state().events[31].id==33);});
 run("A24 running event cannot ACK, stopped event ACK once",[]{Rig r;r.dry();require(!r.c.acknowledgeEvent(1));r.tick(4000);require(r.c.acknowledgeEvent(1)&&!r.c.acknowledgeEvent(1));require(r.c.state().reservedMs==1000&&r.c.state().starts==1);});
 run("A25 reboot keeps quota and marks interrupted event Reboot",[]{Rig r;r.dry();Store s;Output out;Controller reboot(config(),r.store.saved,s,0,&out);require(!out.on&&!reboot.pumping()&&reboot.state().reservedMs==1000&&reboot.state().events[0].reason==Reason::Reboot);});
 run("A26 offline AUTO remains locally bounded without server calls",[]{Rig r;r.dry();r.tick(4000);require(!r.out.on&&r.c.state().eventCount==1);r.tick(5000);require(!r.out.on);r.tick(6000);require(r.out.on&&r.out.starts==2);r.tick(6100,20,false);require(!r.out.on);});
 run("A27 guard heartbeat tank and duration boundaries",[]{require(guardReason(500,0,1000,0,true)==Reason::Running);require(guardReason(501,0,1000,0,true)==Reason::Guard);require(guardReason(100,0,1000,100,false)==Reason::Tank);require(guardReason(1000,0,1000,1000,true)==Reason::Duration);});
 run("A28 storage failure while stopping keeps fake output OFF",[]{Rig r;r.dry();r.store.ok=false;r.tick(3100,45);require(!r.out.on&&r.c.fault());r.dry(6000);require(r.out.starts==1);});
 run("A29 fresh boot defaults OFF",[]{State s;Rig r(config(),s);r.dry();require(r.c.mode()==Mode::Off&&!r.out.on);});
 // Explicitly characterize resume policy rather than claim every reboot resets mode OFF.
 run("A30 runtime boot disarms saved AUTO until a new mode command",[]{Rig r;r.dry();Store s;Output out;Controller reboot(config(),r.store.saved,s,0,&out);require(reboot.disarmAfterBoot()&&reboot.mode()==Mode::Off&&s.saved.mode==Mode::Off);for(unsigned t=1000;t<=3000;t+=1000)reboot.tick(t,epoch+10,sample(t));require(!out.on&&reboot.state().starts==1);});
 run("A31 NaN infinity and out of range during AUTO stop as Sensor",[]{for(float v:{NAN,INFINITY,-1.f,101.f}){Rig r;r.dry();r.tick(3100,v);require(!r.out.on&&r.c.state().events[0].reason==Reason::Sensor);}});
 run("A32 millis rollover preserves AUTO pulse deadline",[]{Store store;Output out;Controller c(config(),automatic(),store,UINT32_MAX-4000,&out);for(uint32_t t:{UINT32_MAX-2500,UINT32_MAX-1500,UINT32_MAX-500})c.tick(t,epoch,sample(t));require(out.on);c.tick(498,epoch+1,sample(498));require(out.on);c.tick(499,epoch+1,sample(499));require(!out.on&&c.state().events[0].actualMs==1000);});
 run("A33 failed normal ACK cannot block STOP or release new starts",[]{
   CommandDelivery d;d.dispatched(false);require(d.shouldPoll()&&!d.canDispatch(false)&&d.canDispatch(true));
   d.receivedAck(false);
   for(int status:{-1,404,500}) {d.ackResult(false,status);require(d.normalPending&&d.shouldPoll()&&d.canDispatch(true)&&!d.canDispatch(false));}
   Rig r;r.dry();d.dispatched(true);require(!d.shouldPoll());
   r.c.command(command(Command::Kind::Stop,10),3100,epoch,sample(3100));
   d.receivedAck(true);d.ackResult(true,500);require(!r.out.on&&!d.shouldPoll());
   d.ackResult(true,200);require(d.shouldPoll()&&d.canDispatch(true)&&!d.canDispatch(false));
   d.ackResult(false,204);require(d.canDispatch(false));
 });
 run("A34 expired OFF fences older queued AUTO across reboot",[]{Rig r;r.dry();auto stop=command(Command::Kind::SetMode,10);stop.expiresAt=epoch-1;r.c.command(stop,3100,0,sample(3100));
   auto older=command(Command::Kind::SetMode,9,Mode::Auto);r.c.command(older,3200,epoch,sample(3200));r.dry(6000);require(!r.out.on&&r.c.mode()==Mode::Off&&r.c.state().lastCommand==10);
   Store store;Controller reboot(config(),r.store.saved,store,0);require(reboot.disarmAfterBoot());reboot.command(older,1000,epoch,sample(1000));require(reboot.mode()==Mode::Off);
 });
 run("A35 failed boot disarm persistence blocks rearming",[]{Store store;Output out;store.ok=false;Controller c(config(),automatic(),store,0,&out);require(!c.disarmAfterBoot()&&c.fault()&&!out.on);store.ok=true;c.command(command(Command::Kind::SetMode,1,Mode::Auto),0,epoch,sample(0));for(unsigned t=1000;t<=3000;t+=1000)c.tick(t,epoch,sample(t));require(!out.on);});
 run("A36 only STOP and OFF qualify for priority delivery",[]{require(isSafetyCommand(command(Command::Kind::Stop)));require(isSafetyCommand(command(Command::Kind::SetMode)));require(!isSafetyCommand(command(Command::Kind::SetMode,1,Mode::Auto)));require(!isSafetyCommand(command(Command::Kind::Water)));});
 std::cout<<"SUMMARY | "<<pass<<" PASS | "<<fail<<" FAIL | host-only fake output\n";
 return fail?1:0;
}
