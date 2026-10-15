import test from "node:test";
import assert from "node:assert/strict";
import {mapModel,signal,quality} from "../www/gwi-map-model.js";

function point(scope,id,name="Sala") {return {state:"2",attributes:{gwi_scope:scope,gwi_item_id:id,gwi_kind:"point",gwi_metric:"clients",device_name:name,online:true,data_source:"google_cloud"}};}
function client(scope,id,ap,rssi) {return {state:"Sala",attributes:{gwi_scope:scope,gwi_item_id:id,gwi_kind:"client",gwi_metric:"point",device_name:id,connected:true,ap_id:ap,point:"Sala",rssi}};}

test("unknown data never receives green signal",()=>{
  for(const value of [null,undefined,"",true,50,"NaN",-200]) assert.equal(signal(value).key,"unknown");
  assert.equal(signal(-45,true).key,"unknown");
  assert.equal(signal(-45,false,true).bars,0);
});
test("explicit dBm has a labeled indication",()=>{
  assert.equal(signal(-48).bars,4); assert.equal(signal(-64).key,"good"); assert.equal(signal(-72).key,"fair"); assert.equal(signal(-83).key,"weak");
});
test("Shelly measured RSSI wins for bars while Google quality remains separate",()=>{
  const c=client("a","shelly","ap1",-78);
  Object.assign(c.attributes,{rssi_source:"shelly_wifi_status",rssi_observed_at:"2026-10-12T12:00:00Z",signal_quality:"excellent",quality_source:"google_connection_rating",gwi_device_id:"own-device",roaming_supported:true,radio_available:true,wifi_channel:6,wifi_bssid:"11:22:33:44:55:66"});
  const model=mapModel({"sensor.ap":point("a","ap1"),"sensor.client":c})[0],device=model.clients[0];
  assert.equal(device.signal.key,"weak"); assert.equal(device.signal.rssi,-78);
  assert.equal(device.googleQuality.key,"excellent"); assert.equal(device.roaming,true);
  assert.equal(device.ownDeviceId,"own-device"); assert.equal(model.rssiClients,1);
});
test("AP bindings use explicit IDs within each network",()=>{
  const model=mapModel({"sensor.ap_a":point("a","ap1"),"sensor.ap_b":point("b","ap1"),"sensor.phone":client("a","phone","ap1",-72)});
  assert.equal(model.find(n=>n.scope==="a").points[0].clients.length,1);
  assert.equal(model.find(n=>n.scope==="b").points[0].clients.length,0);
});
test("unknown AP stays unassigned even if a name matches",()=>{
  const model=mapModel({"sensor.ap":point("a","ap1"),"sensor.phone":client("a","phone","unknown",-64)})[0];
  assert.equal(model.points[0].clients.length,0); assert.equal(model.unassigned.length,1);
});
test("offline/failed samples do not draw stale client links",()=>{
  const p=point("a","ap1"), c=client("a","phone","ap1",-45); c.state="unavailable"; p.state="unavailable";
  const model=mapModel({"sensor.ap":p,"sensor.phone":c})[0];
  assert.equal(model.clients.length,0); assert.equal(model.points[0].online,null); assert.equal(model.points[0].count,null);
});

test("a partially unavailable account keeps the healthy map and never shows cached links as live",()=>{
  const identity=(scope,kind,id,metric,name)=>({gwi_scope:scope,gwi_kind:kind,gwi_item_id:id,gwi_metric:metric,device_name:name,data_source:"google_cloud"});
  const states={
    "sensor.healthy":{state:"quality_data_available",attributes:identity("healthy","network","n1","diagnosis","Example network A")},
    "sensor.healthy_point":point("healthy","ap1","Example point A"),
    "sensor.healthy_client":client("healthy","phone","ap1",-55),
    "sensor.failed":{state:"unavailable",attributes:identity("failed","network","n2","diagnosis","Example network B")},
    "sensor.failed_point":{state:"unavailable",attributes:identity("failed","point","ap2","clients","Example point B")},
    "sensor.failed_client":{state:"unavailable",attributes:identity("failed","client","tablet","point","Example tablet")},
  };
  const model=mapModel(states);
  assert.equal(model.find(n=>n.scope==="healthy").clients.length,1);
  const failed=model.find(n=>n.scope==="failed");
  assert.equal(failed.unavailable,true);
  assert.equal(failed.name,"Example network B");
  assert.equal(failed.points.length,1);
  assert.equal(failed.points[0].online,null);
  assert.equal(failed.points[0].count,null);
  assert.equal(failed.points[0].mesh.key,"unknown");
  assert.equal(failed.clients.length,0);
  assert.equal(mapModel(states,{network_entity:"sensor.failed"})[0].scope,"failed");
});
test("mesh quality stays unknown even when all client signal is good",()=>{
  const model=mapModel({"sensor.ap":point("a","ap1"),"sensor.phone":client("a","phone","ap1",-45)})[0];
  assert.equal(model.points[0].mesh.key,"unknown"); assert.equal(model.points[0].mesh.bars,0);
});
test("Google connection ratings color clients without fabricating dBm",()=>{
  const c=client("a","phone","ap1",undefined);
  Object.assign(c.attributes,{signal_quality:"weak",quality_source:"google_connection_rating",wireless_band:"BAND_2400_MHZ"});
  const model=mapModel({"sensor.ap":point("a","ap1"),"sensor.phone":c},{},"pt")[0];
  assert.equal(model.clients[0].signal.key,"weak"); assert.equal(model.clients[0].signal.rssi,undefined);
  assert.equal(model.clients[0].band,"2,4 GHz"); assert.equal(model.weakClients,1);
  assert.equal(quality("excellent","unverified").key,"unknown");
});
test("mesh comparisons use a unique explicit root in the same network",()=>{
  const root=point("a","root","Sala"),leaf=point("a","leaf","Cozinha"),foreign=point("b","leaf","Outra rede");
  Object.assign(root.attributes,{is_root:true,root_ap_id:"root"});
  Object.assign(leaf.attributes,{is_root:false,root_ap_id:"root",mesh_quality:"fair",mesh_quality_source:"google_mesh_rating"});
  const networks=mapModel({"sensor.root":root,"sensor.leaf":leaf,"sensor.other":foreign});
  assert.deepEqual(networks.find(n=>n.scope==="a").meshLinks.map(l=>({from:l.from,to:l.to,key:l.quality.key})),[{from:"root",to:"leaf",key:"fair"}]);
  assert.equal(networks.find(n=>n.scope==="b").meshLinks.length,0);
});
test("offline mesh readings stay neutral and wired clients have no radio bars",()=>{
  const p=point("a","ap1"),c=client("a","wired","ap1",-45);
  Object.assign(p.attributes,{online:false,mesh_quality:"excellent",mesh_quality_source:"google_mesh_rating"});
  Object.assign(c.attributes,{connection_type:"WIRED",signal_quality:"excellent",quality_source:"google_connection_rating"});
  const model=mapModel({"sensor.ap":p,"sensor.c":c},{},"pt")[0];
  assert.equal(model.points[0].mesh.key,"unknown"); assert.equal(model.clients[0].signal.bars,0);
  assert.match(model.clients[0].signal.label,/Cabo/);
});

test("HA aliases, IP, MAC and zero traffic survive the map model",()=>{
  const c=client("a","opaque","ap1",undefined);
  Object.assign(c.attributes,{device_name:"Kitchen Light",google_name:"0123456789ab*",name_source:"home_assistant",ha_device_id:"ha-lamp",ip_address:"192.168.50.2",mac_address:"aa:bb:cc:dd:ee:ff",download_mbps:0,upload_mbps:0});
  const device=mapModel({"sensor.ap":point("a","ap1"),"sensor.client":c})[0].clients[0];
  assert.equal(device.name,"Kitchen Light"); assert.equal(device.nameSource,"home_assistant");
  assert.equal(device.ip,"192.168.50.2"); assert.equal(device.mac,"aa:bb:cc:dd:ee:ff");
  assert.equal(device.download,0); assert.equal(device.upload,0); assert.equal(device.matchedDeviceId,"ha-lamp");
});
