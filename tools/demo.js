// Fictional fixtures only. All service responses are local JavaScript objects.
import '../custom_components/google_wifi_insights/frontend/google-wifi-insights-panel.js';

const panel=document.querySelector('#panel');
let tick=0;
const entities={};
const now=()=>new Date().toISOString();
const demoAreas=[{id:'office',name:'Example office'},{id:'studio',name:'Example studio'},{id:'hall',name:'Example hall'}];
const areaMappings={point0:'hall',point1:'office',point2:'studio'};
const demoNaming={enabled:false,paused_reason:null,history:[],excluded_station_ids:[]};
let demoGoogleName='Unnamed device';
const namingSummary=()=>({enabled:demoNaming.enabled,paused_reason:null,last_state:demoNaming.history.at(-1)?.state||'idle',verified_count:demoNaming.history.filter(r=>r.state==='verified').length,unconfirmed_count:0});
function demoRename(){const record={request_id:'demo-name-'+(demoNaming.history.length+1),station_id:'client5',old_name:demoGoogleName,new_name:'Example tablet',state:'verified',kind:'rename',automatic:demoNaming.enabled};demoGoogleName=record.new_name;demoNaming.history.push(record);return record;}
function management(){
 return {scope:'example',network_id:'example',name:'Example WiFi',entity_id:'sensor.demo_example_network_network_diagnosis',areas:demoAreas,
  points:['Main point','Office point','Studio point'].map((name,i)=>({id:`point${i}`,name,entity_id:`sensor.demo_example_point_point${i}_clients`,area_id:areaMappings[`point${i}`],online:true,is_root:i===0})),
  name_candidates:demoGoogleName==='Unnamed device'?[{station_id:'client5',entity_id:'sensor.demo_example_client_client5_point',google_name:demoGoogleName,proposed_name:'Example tablet',mac_address:'02:00:00:00:00:06'}]:[],rename:{...demoNaming,...namingSummary(),state:'schema_verified_android_client',provider_state:'demo_only',writable:true}};
}
function state(scope,kind,id,key,value,name,extra={}){
  const entityId=`sensor.demo_${scope}_${kind}_${id}_${key}`;
  entities[entityId]={entity_id:entityId,state:String(value),last_updated:now(),attributes:{gwi_scope:scope,gwi_network_id:scope,gwi_kind:kind,gwi_item_id:id,gwi_metric:key,device_name:name,data_source:'google_cloud',...extra}};
  return entityId;
}
function history(mode='hour'){
  const size={minute:60,hour:24,day:7,month:30}[mode],step={minute:60,hour:3600,day:86400,month:86400}[mode]*1000;
  const end=Date.now(),start=end-size*step;
  return {period:{start:new Date(start).toISOString(),end:new Date(end).toISOString(),expected_buckets:size,granularity_seconds:step/1000},retrieved_at:now(),series:Array.from({length:size},(_,i)=>({start:new Date(start+i*step).toISOString(),end:new Date(start+(i+1)*step).toISOString(),download_bytes:Math.round(200000000+120000000*(1+Math.sin(i*.7))),upload_bytes:Math.round(20000000+15000000*(1+Math.cos(i*.4)))}))};
}
function build(){
  for(const key of Object.keys(entities))delete entities[key];
  const scope='example',names=['Main point','Office point','Studio point'];
  const rows=[['Example laptop',0,-52,'excellent'],['Example television',0,null,'fair'],['Example phone',0,-64,'fair'],['Example workstation',1,-48,'excellent'],['Example speaker',1,-77,'weak'],['Example tablet',1,null,null],['Example thermostat',2,-62,'fair'],['Example console',2,-58,'excellent']];
  const summary=history(),usage={period:summary.period,retrieved_at:summary.retrieved_at};
  const networkInfo={cloud:{lan_settings:{ipAddress:'192.0.2.1',netmask:'255.255.255.0',dhcpPoolBegin:'192.0.2.10',dhcpPoolEnd:'192.0.2.200',upnpEnabled:false},wan_properties:{wanMode:'DHCP',ipAddress:'198.51.100.10',gateway:'198.51.100.1'},wan_settings:{dnsConfig:{dnsMode:'AUTOMATIC'},ipv6Enabled:true},guest_wifi:{enabled:false}},retrieved_at:now(),demo_fields:Object.fromEntries(Array.from({length:40},(_,i)=>[`example_field_${i}`,`Fictional value ${i}; refresh ${tick}`]))};
  state(scope,'network','network','diagnosis','quality_data_available','Example WiFi',{name_sync:namingSummary()});
  state(scope,'network','network','connected_clients',rows.length,'Example WiFi');
  state(scope,'network','network','download_mbps',(12.4+tick/100).toFixed(2),'Example WiFi');
  state(scope,'network','network','upload_mbps','1.8','Example WiFi');
  state(scope,'network','network','wan_status','online','Example WiFi');
  state(scope,'network','network','google_telemetry_at',now(),'Example WiFi',{google_telemetry:{usage_windows:{hour:usage},usage_hourly:summary.series,networkInformation:networkInfo}});
  state(scope,'network','network','network_information_status','available','Example WiFi',{network_information:networkInfo});
  names.forEach((name,i)=>{
    const firmware={installed_version:'123.4.5',local_version:'123.4.5',update_status:'idle',update_channel:'stable',update_required:false,lan_stale:false,lan_retrieved_at:now(),release_notes:{state:'available',queried_version:'123.4.5',matching_installed:true,notes:[{version:'123.4.5',title:'Example release notes',description:'Fictional firmware note used to demonstrate this view.',matches_installed:true}]}};
    const lan={host:`192.0.2.${i+1}`,stale:false,retrieved_at:now(),status:{system:{groupRole:i===0?'root':'leaf',uptime:86400},wan:{online:true,ethernetLink:true,ipMethod:'dhcp',localIpAddress:`192.0.2.${i+1}`,gatewayIpAddress:'192.0.2.1'}},endpoints:{status:{state:'available',stale:false,retrieved_at:now()}}};
    const area=demoAreas.find(a=>a.id===areaMappings[`point${i}`]);
    state(scope,'point',`point${i}`,'clients',rows.filter(row=>row[1]===i).length,name,{online:true,is_root:i===0,root_ap_id:'point0',mesh_quality:i===2?'fair':'excellent',mesh_quality_source:'google_mesh_rating',mapped_area:area?.name,mapped_area_id:area?.id});
    state(scope,'point',`point${i}`,'google_telemetry_at',now(),name,{google_telemetry:{firmwareInformation:firmware,lanInformation:lan}});
    state(scope,'point',`point${i}`,'update_status','idle',name,{firmware_information:firmware});
    state(scope,'point',`point${i}`,'lan_status','available',name,{lan_information:lan});
  });
  rows.forEach(([name,point,rssi,quality],i)=>{
    if(document.querySelector('#scenario').value==='missing'){rssi=null;quality=null;}
    state(scope,'client',`client${i}`,'point',names[point],name,{connected:true,ap_id:`point${point}`,point:names[point],rssi,rssi_source:rssi==null?null:'shelly_wifi_status',rssi_observed_at:rssi==null?null:now(),signal_quality:quality,quality_source:'google_connection_rating',wireless_band:'BAND_5000_MHZ',connection_type:'WIRELESS',ip_address:`192.0.2.${i+10}`,mac_address:`02:00:00:00:00:${String(i+1).padStart(2,'0')}`,download_mbps:i===0?3.5+tick/100:Math.max(0,1-i/10),upload_mbps:.1,google_name:name,ha_device_name:i===0?'Example computer':null,wifi_test_mbps:120+i*20,wifi_test_at:now(),wifi_test_point:names[point],usage_windows:{hour:usage},usage_hourly:summary.series});
    const area=demoAreas.find(a=>a.id===areaMappings[`point${point}`]);
    Object.assign(entities[`sensor.demo_example_client_client${i}_point`].attributes,{associated_area:area?.name,associated_area_id:area?.id,area_source:area?'wifi_point':null});
    if(i===5)Object.assign(entities[`sensor.demo_example_client_client${i}_point`].attributes,{google_name:demoGoogleName,ha_device_name:'Example tablet',device_name:demoGoogleName==='Unnamed device'?'Unnamed device (Example tablet)':demoGoogleName});
  });
  if(document.querySelector('#scenario').value==='partial'){
    state('unavailable-example','network','network','diagnosis','unavailable','Second example network');
    state('unavailable-example','point','old-point','clients','unavailable','Unavailable example point');
  }
  return {language:document.querySelector('#language').value,locale:{language:document.querySelector('#language').value},config:{time_zone:'UTC'},user:{is_admin:true},states:entities,callWS:async request=>{
   if(request.service==='get_management')return {response:management()};
   if(request.service==='set_point_area'){const point=management().points.find(p=>p.entity_id===request.service_data.entity_id);if(!point)throw Error('Unknown demo point');areaMappings[point.id]=request.service_data.area_id;return {response:management()};}
   if(['set_name_sync','rename_client','undo_name','verify_name'].includes(request.service)){
    let result=null;
    if(request.service==='set_name_sync'){demoNaming.enabled=request.service_data.enabled;if(demoNaming.enabled&&demoGoogleName==='Unnamed device'&&!demoNaming.excluded_station_ids.includes('client5'))result=demoRename();}
    if(request.service==='rename_client'){if(demoGoogleName!==request.service_data.expected_google_name||request.service_data.expected_mac!=='02:00:00:00:00:06'||request.service_data.expected_ha_name!=='Example tablet')throw Error('Demo preview changed');result=demoRename();}
    if(request.service==='undo_name'){const original=demoNaming.history.find(r=>r.request_id===request.service_data.request_id);if(!original||demoGoogleName!==original.new_name)throw Error('Demo name changed');result={...original,request_id:'demo-undo',old_name:original.new_name,new_name:original.old_name,kind:'undo',automatic:false};demoGoogleName=original.old_name;demoNaming.history.push(result);demoNaming.excluded_station_ids.push('client5');}
    if(request.service==='verify_name')result=demoNaming.history.find(r=>r.request_id===request.service_data.request_id);
    panel.hass=build();return {response:{...management(),name_result:result}};
   }
   if(request.service==='google_action')throw Error('Demo mode: network actions are disabled');
   return {response:history(request.service_data?.resolution)};
  },callService:async()=>{throw new Error('Demo mode: network actions are disabled');}};
}
function update(){panel.hass=build();}
panel.panel={config:{map_path:'/google-wifi-insights/mapa'}};
panel.route={path:'/mapa'};
document.querySelector('#language').addEventListener('change',update);
document.querySelector('#scenario').addEventListener('change',update);
document.addEventListener('hass-more-info',event=>{
  document.querySelector('#detail-text').textContent=JSON.stringify(entities[event.detail.entityId]||{demo:true},null,2);
  document.querySelector('#details').showModal();
});
update();
setInterval(()=>{tick++;update();},3000);
