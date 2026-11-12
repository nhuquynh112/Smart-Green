const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function setup(sharedStorage=new Map()){
  const elements=new Map();
  const el=id=>{if(!elements.has(id))elements.set(id,{value:'',textContent:'',classList:{add(){},remove(){}}});return elements.get(id);};
  let posts=0, finishPost, chart, getError=false, hangGet=false;
  const requests=[],timers=new Map();let timerId=0;
  function Chart(element,config){Object.assign(this,config);this.update=()=>{};chart=this;}
  const data={device:{device_id:'garden',connected:true,last_seen_at:new Date().toISOString()},latest:{mode:'OFF',water_ok:true,soil_valid:true,clock_ready:true,commissioned:true,received_at:new Date().toISOString(),measured_at:new Date().toISOString()},commands:[]};
  const context={Uint8Array,crypto:require('node:crypto').webcrypto,localStorage:{getItem:k=>sharedStorage.get(k)||null,setItem:(k,v)=>sharedStorage.set(k,v),removeItem:k=>sharedStorage.delete(k)},document:{getElementById:el,activeElement:null},window:{Chart},Chart,sessionStorage:{getItem:()=> 'test',setItem(){},removeItem(){}},Date,Number,Math,JSON,encodeURIComponent,AbortController,setTimeout(fn){timers.set(++timerId,fn);return timerId;},clearTimeout(id){timers.delete(id);},setInterval(){},fetch:async(url,options)=>{
    if(options.method==='POST'){posts++;const seq=posts;await new Promise((resolve,reject)=>{finishPost=resolve;requests.push({resolve,reject,body:JSON.parse(options.body)});options.signal.addEventListener('abort',()=>reject(new Error('aborted')));});return {ok:true,status:201,json:async()=>({command_seq:seq})};}
    if(hangGet)await new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('aborted'))));
    if(getError)throw new Error('NetworkError');
    for(const c of data.commands){if(!c.request_id)c.request_id=requests[c.command_seq-1]?.body.request_id;}
    if(url.includes('/requests/')){const c=data.commands.find(c=>c.request_id===url.split('/').at(-1));return {ok:!!c,status:c?200:404,json:async()=>c||{detail:'not found'}};}
    return {ok:true,status:200,json:async()=>data};
  }};
  let source=fs.readFileSync('backend/static/index.html','utf8').split('<script>').at(-1).split('</script>')[0];
  source=source.replace(/loadDevices\(\)\.catch\(e=>notice\(e.message,'error'\)\);setInterval\([^\n]+/,'');
  source=source.replace('})();',"globalThis.apiTest={render,createCommand,refresh,select(id){selected=id;}};})();");
  el('waterSeconds').value='0.5';vm.runInNewContext(source,context);context.apiTest.select('garden');
  const render=context.apiTest.render;context.apiTest.render=d=>{for(const c of d.commands||[]){if(!c.request_id)c.request_id=requests[c.command_seq-1]?.body.request_id;}return render(d);};context.apiTest.render(data);
  return {sharedStorage,requests,timers,hangGet(value){hangGet=value;},expire(){for(const fn of [...timers.values()])fn();},failGet(value){getError=value;},chart:()=>chart,api:context.apiTest,el,data,posts:()=>posts,finish:()=>finishPost()};
}
test('polling preserves an edited mode and OFF blocks WATER',()=>{
 const s=setup();s.el('modeSelect').value='MANUAL';s.el('modeSelect').onchange();s.api.render(s.data);
 assert.equal(s.el('modeSelect').value,'MANUAL');assert.equal(s.el('modeNow').textContent,'OFF');assert.equal(s.el('waterBtn').disabled,true);
});
test('one in-flight command, ACK rejection remains visible after polling',async()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.api.render(s.data);
 const first=s.api.createCommand({kind:'WATER',duration_ms:500});
 await s.api.createCommand({kind:'WATER',duration_ms:500});assert.equal(s.posts(),1);
 assert.equal(s.el('waterBtn').disabled,true);
 s.finish();await first;
 assert.match(s.el('commandFeedback').textContent,/đang chờ/);
 s.data.commands=[{command_seq:1,status:'ACKED',ack_result:'cooldown'}];s.api.render(s.data);s.api.render(s.data);
 assert.match(s.el('commandFeedback').textContent,/thời gian nghỉ/);
});
test('expired command reports expiry rather than success',async()=>{
 const s=setup();const request=s.api.createCommand({kind:'SET_MODE',mode:'MANUAL'});s.finish();await request;
 s.data.commands=[{command_seq:1,status:'EXPIRED'}];s.api.render(s.data);
 assert.match(s.el('commandFeedback').textContent,/hết hạn/);
});
test('cooldown telemetry locks watering, then expires without another click',()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.data.latest.received_at=new Date().toISOString();s.data.latest.payload={cooldown_remaining_ms:600000};s.api.render(s.data);
 assert.equal(s.el('waterBtn').disabled,true);assert.match(s.el('waterLock').textContent,/Đang nghỉ/);
 s.data.latest.payload.cooldown_remaining_ms=0;s.api.render(s.data);assert.equal(s.el('waterBtn').disabled,false);
});
test('a newer mode ACK updates controls without waiting for periodic telemetry',()=>{
 const s=setup();s.data.latest.received_at=new Date().toISOString();s.data.latest.uptime_ms=60000;s.data.latest.last_command_seq=1;
 s.data.commands=[{command_seq:2,kind:'SET_MODE',mode:'MANUAL',ack_result:'mode_set',status:'ACKED',issued_at:Math.floor(Date.now()/1000)}];s.api.render(s.data);
 assert.match(s.el('modeNow').textContent,/MANUAL/);assert.equal(s.el('waterBtn').disabled,true);
 s.data.latest.mode='MANUAL';s.data.latest.last_command_seq=2;s.api.render(s.data);assert.equal(s.el('waterBtn').disabled,false);
 s.data.latest.mode='OFF';
 s.data.latest.uptime_ms=0;s.data.latest.received_at=new Date(Date.now()+10000).toISOString();s.api.render(s.data);
 assert.equal(s.el('modeNow').textContent,'OFF');assert.equal(s.el('waterBtn').disabled,true);
});
test('quota blocks watering and displays the actual firmware limit',()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.data.latest.payload={quota_starts:4,quota_limit_starts:4,quota_reserved_ms:2000,quota_limit_ms:4000};s.api.render(s.data);
 assert.equal(s.el('waterBtn').disabled,true);assert.match(s.el('statDaily').textContent,/4 \/ 4/);
 assert.equal(s.el('statWater').textContent,'Chưa hiệu chuẩn');
});

test('OFF does not show the automatic cooldown as a manual watering wait',()=>{
 const s=setup();s.data.latest.payload={cooldown_remaining_ms:600000};s.api.render(s.data);
 assert.equal(s.el('waterBtn').disabled,true);
 assert.doesNotMatch(s.el('waterLock').textContent,/Đang nghỉ/);
 assert.match(s.el('waterLock').textContent,/MANUAL/);
});
test('chart preserves elapsed time and breaks missing-data intervals',()=>{
 const s=setup();const t=Date.now();
 s.data.history=[0,30000,300000].map(offset=>({measured_at:new Date(t+offset).toISOString(),soil_valid:true,soil_pct:20,air_valid:true,temperature_c:30}));
 s.api.render(s.data);const chart=s.chart();
 assert.equal(chart.options.scales.x.type,'linear');
 const points=chart.data.datasets[0].data;
 assert.equal(points.length,4);assert.equal(points[2].y,null);
 assert.equal(points[3].x-points[0].x,300000);
});
test('device and command strings render as text instead of HTML',()=>{
 const s=setup();const unsafe='<img src=x onerror=alert(1)>';
 s.data.latest.boot_id=unsafe;s.data.commands=[{command_seq:1,kind:unsafe,status:'ACKED',ack_result:unsafe}];
 s.data.watering_events=[{source:unsafe,reason:unsafe,actual_ms:500}];s.api.render(s.data);
 for(const id of ['hardwareGrid','commandsBody','eventsBody']){
  assert.doesNotMatch(s.el(id).innerHTML,/<img/);assert.match(s.el(id).innerHTML,/&lt;img/);
 }
});

test('chart excludes overnight history and retains a single current sample',()=>{
 const s=setup();const end=Date.now();
 s.data.history=[-12*3600000,0].map(offset=>({measured_at:new Date(end+offset).toISOString(),soil_valid:true,soil_pct:1,air_valid:true,temperature_c:31.7}));
 s.api.render(s.data);const chart=s.chart();
 assert.equal(chart.data.datasets[0].data.length,1);
 assert.equal(chart.data.datasets[0].data[0].x,end);
 assert.equal(chart.options.scales.x.min,end-1800000);
 assert.equal(chart.options.scales.x.max,end);
});

test('zero count limit permits manual starts but still enforces time budget',()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.data.latest.payload={quota_starts:20,quota_limit_starts:0,quota_reserved_ms:4000,quota_limit_ms:20000};s.api.render(s.data);
 assert.equal(s.el('waterBtn').disabled,false);assert.match(s.el('statDaily').textContent,/Không giới hạn số lần/);
 s.data.latest.payload.quota_reserved_ms=20000;s.api.render(s.data);assert.equal(s.el('waterBtn').disabled,true);
});

test('failed refresh locks WATER and clears only its notice on recovery',async()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.api.render(s.data);
 assert.equal(s.el('waterBtn').disabled,false);
 s.failGet(true);await s.api.refresh();assert.equal(s.el('waterBtn').disabled,true);
 assert.match(s.el('notice').textContent,/NetworkError/);
 s.failGet(false);await s.api.refresh();assert.equal(s.el('waterBtn').disabled,false);
 assert.equal(s.el('notice').className,'notice');
});

test('changing device cannot send WATER using the previous device readiness',async()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.api.render(s.data);
 s.api.select('different-device');await s.api.createCommand({kind:'WATER',duration_ms:500});
 assert.equal(s.posts(),0);
});


test('hung refresh times out, locks WATER, and polling recovers',async()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.api.render(s.data);s.hangGet(true);
 const request=s.api.refresh();s.expire();await request;
 assert.equal(s.el('waterBtn').disabled,true);assert.match(s.el('notice').textContent,/10 giây/);
 s.hangGet(false);await s.api.refresh();assert.equal(s.el('waterBtn').disabled,false);assert.equal(s.timers.size,0);
});
test('lost POST response reconciles the exact persisted request identity',async()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.api.render(s.data);
 const request=s.api.createCommand({kind:'WATER',duration_ms:500});s.expire();await request;
 await s.api.createCommand({kind:'WATER',duration_ms:500});assert.equal(s.posts(),1);assert.equal(s.el('waterBtn').disabled,true);
 s.data.commands=[{command_seq:1,kind:'WATER',duration_ms:500,status:'ACKED',ack_result:'started'}];await s.api.refresh();
 assert.equal(s.el('waterBtn').disabled,false);assert.match(s.el('commandFeedback').textContent,/Lệnh #1/);
});
test('late WATER response cannot replace newer STOP tracking',async()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.api.render(s.data);
 const water=s.api.createCommand({kind:'WATER',duration_ms:500});
 const stop=s.api.createCommand({kind:'STOP'});
 s.requests[1].resolve();await stop;s.requests[0].resolve();await water;
 assert.match(s.el('commandFeedback').textContent,/#2/);
 s.data.commands=[{command_seq:2,kind:'STOP',status:'ACKED',ack_result:'stopped'}];s.api.render(s.data);
 assert.match(s.el('commandFeedback').textContent,/tắt đầu ra/);
});

test('uncertain WATER ignores unrelated commands and still permits STOP',async()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.api.render(s.data);
 const water=s.api.createCommand({kind:'WATER',duration_ms:500});s.expire();await water;
 s.data.commands=[{command_seq:2,kind:'SET_MODE',mode:'MANUAL',status:'ACKED',ack_result:'mode_set'}];await s.api.refresh();
 assert.equal(s.el('waterBtn').disabled,true);
 const stop=s.api.createCommand({kind:'STOP'});assert.equal(s.posts(),2);s.finish();await stop;
 assert.match(s.el('commandFeedback').textContent,/#2/);
});

test('reload and another tab retain pending identity without a second POST',async()=>{
 const first=setup();first.data.latest.mode='MANUAL';first.api.render(first.data);
 const request=first.api.createCommand({kind:'WATER',duration_ms:500});
 const id=first.requests[0].body.request_id;
 const reload=setup(first.sharedStorage);reload.data.latest.mode='MANUAL';reload.api.render(reload.data);
 await reload.api.createCommand({kind:'WATER',duration_ms:500});assert.equal(reload.posts(),0);
 // Same contents but another request identity must never unlock this request.
 reload.data.commands=[{command_seq:10,request_id:'other-request-id',kind:'WATER',duration_ms:500,status:'ACKED',ack_result:'started'}];
 await reload.api.refresh();assert.equal(reload.el('waterBtn').disabled,true);
 reload.data.commands=[{command_seq:11,request_id:id,kind:'WATER',duration_ms:500,status:'ACKED',ack_result:'started'}];
 await reload.api.refresh();assert.equal(reload.el('waterBtn').disabled,false);
 assert.equal(first.sharedStorage.size,0);
 first.finish();await request;
});


test('a STOP resolved in another tab clears the original tab uncertainty',async()=>{
 const s=setup();s.data.latest.mode='MANUAL';s.api.render(s.data);
 const first=s.api.createCommand({kind:'WATER',duration_ms:500});s.expire();await first;
 assert.equal(s.el('waterBtn').disabled,true);
 // Another tab has reconciled STOP and removed the shared pending request.
 s.sharedStorage.clear();s.data.latest.mode='OFF';s.data.commands=[];
 await s.api.refresh();s.el('modeSelect').value='MANUAL';s.el('modeSelect').onchange();
 assert.equal(s.el('modeBtn').disabled,false);
});
