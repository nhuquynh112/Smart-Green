// Host-only simulator: shared controller/protocol, no Arduino, GPIO, Wi-Fi or real NVS.
#include "controller.h"
#include "protocol.h"
#include "pump_guard.h"
#include <iostream>
#include <memory>
#include <string>
using namespace garden;
struct Store : Storage {
  State saved;bool ok=true;
  bool save(const State& s) override {if(ok)saved=s;return ok;}
};
int main() {
  Store store;Config cfg;cfg.commissioned=true;cfg.cooldownMs=1000;cfg.pulseMs=1000;cfg.maxPulseMs=3000;
  std::unique_ptr<Controller> core(new Controller(cfg,store.saved,store,0));
  std::string line;
  while(std::getline(std::cin,line)) {
    JsonDocument request,response;
    if(deserializeJson(request,line)) {std::cout<<"{\"error\":\"json\"}"<<std::endl;continue;}
    uint32_t ms=request["ms"]|0U;int64_t utc=request["utc"]|1800000001LL;
    Sensor sensor;sensor.soil=request["soil"]|20.0f;sensor.valid=request["valid"]|true;
    sensor.tankOK=request["tank_ok"]|true;sensor.sampledMs=request["sampled_ms"]|ms;
    std::string op=request["op"]|"tick";
    if(op=="command") {
      Command command;const char* error=protocol::parse(request["payload"],"garden-01",cfg.maxPulseMs,command);
      response["result"]=error?error:core->command(command,ms,utc,sensor);
    } else if(op=="reboot") {
      core.reset(new Controller(cfg,store.saved,store,ms));response["result"]="rebooted_simulated_storage";
    } else if(op=="ack_event") response["acknowledged"]=core->acknowledgeEvent(request["event_id"].as<uint32_t>());
    else if(op=="storage_fail") store.ok=false;
    else if(op=="tick") core->tick(ms,utc,sensor);
    else if(op=="guard") core->externalStop(ms,Reason::Guard);
    else response["error"]="unknown_op";
    response["simulation"]=true;response["pump_on"]=core->pumping();response["fault"]=core->fault();
    response["mode"]=protocol::mode(core->mode());response["last_command_seq"]=core->state().lastCommand;
    response["starts_reserved"]=core->state().starts;
    JsonArray events=response["events"].to<JsonArray>();
    for(unsigned i=0;i<core->state().eventCount;++i) {
      const Event& e=core->state().events[i];JsonObject j=events.add<JsonObject>();
      j["schema_version"]=1;j["device_id"]="garden-01";j["event_id"]=e.id;j["command_seq"]=e.commandSeq;
      j["started_at"]=e.startedAt;j["planned_ms"]=e.plannedMs;
      if(e.reason==Reason::Reboot)j["actual_ms"]=nullptr;else j["actual_ms"]=e.actualMs;
      j["source"]=protocol::source(e.source);j["reason"]=protocol::reason(e.reason);
    }
    std::string output;serializeJson(response,output);std::cout<<output<<std::endl;
  }
}
