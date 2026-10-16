// Fictional fixtures only. All service responses are local JavaScript objects.
import './demo-icons.js';
import '../custom_components/google_wifi_insights/frontend/google-wifi-insights-panel.js';

const panel=document.querySelector('#panel');
let tick=0;
const entities={};
const parameters=new URLSearchParams(location.search);
const capture=parameters.get('capture')==='1';
if(['homes','stress'].includes(parameters.get('scenario')))document.querySelector('#scenario').value=parameters.get('scenario');
if(parameters.get('language')==='pt')document.querySelector('#language').value='pt';
if(parameters.get('theme')==='dark')document.querySelector('#theme').value='dark';
document.documentElement.classList.toggle('capture',capture);
const now=()=>new Date().toISOString();
let names=['Hall point','Office point','Studio point','Upstairs point'];
const shortPointNames=[...names];
const longPointNames=['Example entrance and reception point','Example administration and shared workspace point','ExampleStudioPointWithAnUnusuallyLongContinuousName','Example upstairs landing and guest rooms point'];
const demoAreas=[{id:'hall',name:'Hall'},{id:'office',name:'Office'},{id:'studio',name:'Studio'},{id:'upstairs',name:'Upstairs'}];
const areaMappings={point0:'hall',point1:'office',point2:'studio',point3:'upstairs'};
const demoLocations={example:{id:'demo-home',name:'Example home'},'remote-example':{id:'demo-workshop',name:'Example workshop'},'local-example':{id:'demo-home',name:'Example home'}};
const proposedName='Reading tablet';
const demoNaming={enabled:false,paused_reason:null,history:[],excluded_station_ids:[]};
let demoGoogleName='Unnamed device';
const namingSummary=()=>({enabled:demoNaming.enabled,paused_reason:null,last_state:demoNaming.history.at(-1)?.state||'idle',verified_count:demoNaming.history.filter(r=>r.state==='verified').length,unconfirmed_count:0});
function demoRename(automatic=false){const record={request_id:'demo-name-'+(demoNaming.history.length+1),station_id:'client5',mac_address:'02:00:00:00:00:06',old_name:demoGoogleName,new_name:proposedName,state:'verified',kind:'rename',automatic};demoGoogleName=record.new_name;demoNaming.history.push(record);return record;}
function management(scope='example'){
 if(scope==='remote-example')return {scope,network_id:scope,name:'Workshop WiFi',location:demoLocations[scope],entity_id:'sensor.demo_remote-example_network_remote_diagnosis',areas:demoAreas,points:[{id:'point0',name:'Workshop primary',entity_id:'sensor.demo_remote-example_point_point0_clients',area_id:null,online:true,is_root:true},{id:'point1',name:'Annex point',entity_id:'sensor.demo_remote-example_point_point1_clients',area_id:null,online:true,is_root:false}],name_candidates:[],rename:{enabled:false,history:[],writable:true,max_concurrent:3,state:'demo_only'}};
 return {scope:'example',network_id:'example',name:'Demo WiFi',location:demoLocations.example,entity_id:'sensor.demo_example_network_network_diagnosis',areas:demoAreas,
  points:names.map((name,i)=>({id:`point${i}`,name,entity_id:`sensor.demo_example_point_point${i}_clients`,area_id:areaMappings[`point${i}`],online:true,is_root:i===0})),
  name_candidates:demoGoogleName==='Unnamed device'?[{station_id:'client5',entity_id:'sensor.demo_example_client_client5_point',google_name:demoGoogleName,proposed_name:proposedName,mac_address:'02:00:00:00:00:06'}]:[],rename:{...demoNaming,...namingSummary(),max_concurrent:3,state:'schema_verified_android_client',provider_state:'demo_only',writable:true}};
}
function control(kind,id,key,name,domain='button',value='unknown'){
 const sensor=state('example',kind,id,key,value,name,{friendly_name:name});
 const entityId=sensor.replace(/^sensor\./,domain+'.');
 entities[entityId]={...entities[sensor],entity_id:entityId};delete entities[sensor];
}
function state(scope,kind,id,key,value,name,extra={}){
  const entityId=`sensor.demo_${scope}_${kind}_${id}_${key}`;
  entities[entityId]={entity_id:entityId,state:String(value),last_updated:now(),attributes:{gwi_scope:scope,gwi_network_id:scope,gwi_kind:kind,gwi_item_id:id,gwi_metric:key,device_name:name,data_source:'google_cloud',...extra}};
  return entityId;
}
const clientScale=i=>[2,6,10,14,16,20].includes(i)?0.00002:(1-6*0.00002)/18;
const usageSummary=data=>({period:data.period,retrieved_at:data.retrieved_at,complete:true,buckets:data.series.length,expected_buckets:data.period.expected_buckets,download_bytes:data.series.reduce((sum,row)=>sum+row.download_bytes,0),upload_bytes:data.series.reduce((sum,row)=>sum+row.upload_bytes,0)});
function history(mode='hour',scale=1){
  const size={minute:60,hour:24,day:7,month:30}[mode],step={minute:60,hour:3600,day:86400,month:86400}[mode]*1000;
  const end=Date.now(),start=end-size*step;
  const factor=scale*{minute:1/60,hour:1,day:24,month:24}[mode];
  return {period:{start:new Date(start).toISOString(),end:new Date(end).toISOString(),expected_buckets:size,granularity_seconds:step/1000},retrieved_at:now(),series:Array.from({length:size},(_,i)=>({start:new Date(start+i*step).toISOString(),end:new Date(start+(i+1)*step).toISOString(),download_bytes:Math.round((200000000+120000000*(1+Math.sin(i*.7)))*factor),upload_bytes:Math.round((20000000+15000000*(1+Math.cos(i*.4)))*factor)}))};
}
function build(){
  const stress=document.querySelector('#scenario').value==='stress';names=stress?longPointNames:shortPointNames;
  document.documentElement.dataset.theme=document.querySelector('#theme').value;
  for(const key of Object.keys(entities))delete entities[key];
  const scope='example';
  // Measured RSSI belongs only to the six fictional Shelly relays, never phones or laptops.
  const rows=[['Work laptop',0,null,'excellent'],['Media player',0,null,'excellent'],['Hall relay',0,-52,'excellent'],['Doorbell',0,null,'fair'],['Hall speaker',0,null,'good'],['Reading tablet',1,null,null],['Desk lamp relay',1,-77,'weak'],['Desk computer',1,null,'excellent'],['Office printer',1,null,'good'],['Office speaker',1,null,'good'],['Studio relay',2,-62,'good'],['Studio display',2,null,'excellent'],['Music player',2,null,'good'],['Studio sensor',2,null,'fair'],['Upstairs relay',3,-58,'excellent'],['Guest phone',3,null,'good'],['Reading lamp relay',3,-79,'weak'],['E-reader',3,null,'good'],['Thermostat',3,null,'good'],['Hall clock',0,null,'good'],['Office relay',1,-61,'good'],['Game console',2,null,'excellent'],['Bedroom speaker',3,null,null],['Robot vacuum',0,null,'fair']];
  const summary=history();
  const usage=usageSummary(summary);
  const networkInfo={cloud:{lan_settings:{ipAddress:'192.0.2.1',netmask:'255.255.255.0',dhcpPoolBegin:'192.0.2.10',dhcpPoolEnd:'192.0.2.200',upnpEnabled:false},wan_properties:{wanMode:'DHCP',ipAddress:'198.51.100.10',gateway:'198.51.100.1'},wan_settings:{dnsConfig:{dnsMode:'AUTOMATIC'},ipv6Enabled:true},guest_wifi:{enabled:false}},retrieved_at:now(),demo_fields:Object.fromEntries(Array.from({length:40},(_,i)=>[`example_field_${i}`,`Fictional value ${i}; refresh ${tick}`]))};
  state(scope,'network','network','diagnosis','quality_data_available','Demo WiFi',{name_sync:namingSummary()});
  state(scope,'network','network','connected_clients',rows.length,'Demo WiFi');
  state(scope,'network','network','download_mbps',(12.4+tick/100).toFixed(2),'Demo WiFi');
  state(scope,'network','network','upload_mbps','1.8','Demo WiFi');
  state(scope,'network','network','wan_status','WAN_ONLINE','Demo WiFi');
  state(scope,'network','network','wan_test_download_mbps','487.3','Demo WiFi');
  state(scope,'network','network','wan_test_upload_mbps','102.6','Demo WiFi');
  state(scope,'network','network','wan_test_at',now(),'Demo WiFi');
  state(scope,'network','network','google_telemetry_at',now(),'Demo WiFi',{google_telemetry:{usage_windows:{hour:usage},usage_hourly:summary.series,networkInformation:networkInfo}});
  state(scope,'network','network','network_information_status','available','Demo WiFi',{network_information:networkInfo});
  control('network','network','test_internet','Run Internet speed test');
  control('network','network','restart_network','Restart WiFi network');
  names.forEach((name,i)=>{
    const firmware={installed_version:'123.4.5',local_version:'123.4.5',update_status:'idle',update_channel:'stable',update_required:false,lan_stale:false,lan_retrieved_at:now(),release_notes:{state:'available',queried_version:'123.4.5',matching_installed:true,notes:[{version:'123.4.5',title:'Example release notes',description:'Fictional firmware note used to demonstrate this view.',matches_installed:true}]}};
    const lan={host:`192.0.2.${i+1}`,stale:false,retrieved_at:now(),status:{system:{groupRole:i===0?'root':'leaf',uptime:86400},wan:{online:true,ethernetLink:true,ipMethod:'dhcp',localIpAddress:`192.0.2.${i+1}`,gatewayIpAddress:'192.0.2.1'}},endpoints:{status:{state:'available',stale:false,retrieved_at:now()}}};
    const area=demoAreas.find(a=>a.id===areaMappings[`point${i}`]);
    state(scope,'point',`point${i}`,'clients',rows.filter(row=>row[1]===i).length,name,{online:true,is_root:i===0,root_ap_id:'point0',mesh_quality:i===2?'fair':'excellent',mesh_quality_source:'google_mesh_rating',mapped_area:area?.name,mapped_area_id:area?.id});
    state(scope,'point',`point${i}`,'google_telemetry_at',now(),name,{mesh_test_mbps:i?([0,224,156,208][i]):null,mesh_test_at:now(),backhaul_type:i?'wireless':'ethernet',google_telemetry:{firmwareInformation:firmware,lanInformation:lan}});
    state(scope,'point',`point${i}`,'update_status','idle',name,{firmware_information:firmware});
    state(scope,'point',`point${i}`,'lan_status','available',name,{lan_information:lan});
    control('point',`point${i}`,'restart_point','Restart point');
    control('point',`point${i}`,'test_clients','Run client WiFi test');
    if(i)control('point',`point${i}`,'test_mesh','Run mesh test');
  });
  rows.forEach(([name,point,rssi,quality],i)=>{
    if(document.querySelector('#scenario').value==='missing'){rssi=null;quality=null;}
    const clientHistory=history('hour',clientScale(i));
    const clientUsage={hour:usageSummary(clientHistory),day:usageSummary(history('day',clientScale(i))),month:usageSummary(history('month',clientScale(i)))};
    state(scope,'client',`client${i}`,'point',names[point],name,{connected:true,ap_id:`point${point}`,point:names[point],rssi,rssi_source:rssi==null?null:'shelly_wifi_status',rssi_observed_at:rssi==null?null:now(),signal_quality:quality,quality_source:'google_connection_rating',wireless_band:name.includes('relay')||i%3===0?'BAND_2400_MHZ':'BAND_5000_MHZ',connection_type:'WIRELESS',ip_address:`192.0.2.${i+10}`,mac_address:`02:00:00:00:00:${String(i+1).padStart(2,'0')}`,download_mbps:i===0?3.5+tick/100:Math.max(0,1-i/30),upload_mbps:.1,google_name:name,wifi_test_mbps:name.includes('relay')?32+i:120+i*12,wifi_test_at:now(),wifi_test_point:names[point],usage_windows:{hour:usage},usage_hourly:summary.series,roaming_supported:rssi!=null,radio_available:rssi!=null,wifi_channel:rssi==null?null:6,wifi_bssid:rssi==null?null:`02:00:00:01:00:0${point}`});
    const area=demoAreas.find(a=>a.id===areaMappings[`point${point}`]);
    Object.assign(entities[`sensor.demo_example_client_client${i}_point`].attributes,{associated_area:area?.name,associated_area_id:area?.id,area_source:area?'wifi_point':null});
    Object.assign(entities[`sensor.demo_example_client_client${i}_point`].attributes,{usage_windows:clientUsage,usage_hourly:clientHistory.series});
    if(i===5)Object.assign(entities[`sensor.demo_example_client_client${i}_point`].attributes,{google_name:demoGoogleName,ha_device_name:proposedName,device_name:demoGoogleName==='Unnamed device'?`Unnamed device (${proposedName})`:demoGoogleName});
    if(rssi!=null){
     control('client',`client${i}`,'roam_rssi_threshold','Roam signal threshold','number',-70);
     control('client',`client${i}`,'roam_interval','Roam scan interval','number',60);
     control('client',`client${i}`,'roaming_enabled','Roaming enabled','switch','on');
    }
  });
  if(document.querySelector('#scenario').value==='partial'){
    state('unavailable-example','network','network','diagnosis','unavailable','Second example network');
    state('unavailable-example','point','old-point','clients','unavailable','Unavailable example point');
  }
  if(['homes','stress'].includes(document.querySelector('#scenario').value)){
    state('remote-example','network','remote','diagnosis','quality_data_available','Workshop WiFi');
    for(let i=0;i<2;i++)state('remote-example','point','point'+i,'clients',i===0?1:0,i===0?'Workshop primary':'Annex point',{online:true,is_root:i===0,root_ap_id:'point0'});
    state('remote-example','client','tablet','point','Workshop primary','Example work tablet',{connected:true,ap_id:'point0',connection_type:'WIRELESS',ip_address:'198.51.100.20',mac_address:'02:00:00:00:10:20'});
    state('local-example','network','local','diagnosis','insufficient_radio_data','Demo LAN status',{data_source:'local_status'});
    state('local-example','point','local-point','clients','unknown','Hall local status',{data_source:'local_status',online:true,is_root:true});
  }
  for(const s of Object.values(entities))if(s.attributes.gwi_kind==='network'&&s.attributes.gwi_metric==='diagnosis'){
    const location=demoLocations[s.attributes.gwi_scope];Object.assign(s.attributes,{network_location:location?.name||null,network_location_id:location?.id||null,gwi_entry_id:'fictional-entry'});
  }
  return {language:document.querySelector('#language').value,locale:{language:document.querySelector('#language').value},themes:{darkMode:document.querySelector('#theme').value==='dark'},config:{time_zone:'UTC'},user:{is_admin:true},services:{google_wifi_insights:{set_network_location:{}}},states:entities,callWS:async request=>{
   if(request.service==='set_network_location'){
    const target=entities[request.service_data.entity_id];if(target?.attributes.gwi_kind!=='network')throw Error('Unknown demo network');
    const scope=target.attributes.gwi_scope,name=request.service_data.name?.normalize('NFKC').trim().replace(/\s+/g,' ')||null;
    if(name&&name.length>64)throw Error('Invalid demo label');
    demoLocations[scope]=name?{id:'demo-'+name.toLowerCase().replace(/\W/g,'-'),name}:null;
    panel.hass=build();return {response:{scope,location:demoLocations[scope]}};
   }
   if(request.service==='get_management')return {response:management(entities[request.service_data.entity_id]?.attributes.gwi_scope)};
   if(request.service==='set_point_area'){const point=management().points.find(p=>p.entity_id===request.service_data.entity_id);if(!point)throw Error('Unknown demo point');areaMappings[point.id]=request.service_data.area_id;return {response:management()};}
   if(['set_name_sync','rename_client','undo_name','verify_name'].includes(request.service)){
    let result=null;
    if(request.service==='set_name_sync'){demoNaming.enabled=request.service_data.enabled;if(demoNaming.enabled&&demoGoogleName==='Unnamed device'&&!demoNaming.excluded_station_ids.includes('client5'))result=demoRename(true);}
    if(request.service==='rename_client'){if(demoGoogleName!==request.service_data.expected_google_name||request.service_data.expected_mac!=='02:00:00:00:00:06'||request.service_data.expected_ha_name!==proposedName)throw Error('Demo preview changed');result=demoRename();}
    if(request.service==='undo_name'){const original=demoNaming.history.find(r=>r.request_id===request.service_data.request_id);if(!original||demoGoogleName!==original.new_name)throw Error('Demo name changed');result={...original,request_id:'demo-undo',old_name:original.new_name,new_name:original.old_name,kind:'undo',automatic:false};demoGoogleName=original.old_name;demoNaming.history.push(result);demoNaming.excluded_station_ids.push('client5');}
    if(request.service==='verify_name')result=demoNaming.history.find(r=>r.request_id===request.service_data.request_id);
    panel.hass=build();return {response:{...management(),name_result:result}};
   }
   if(request.service==='google_action')throw Error('Demo mode: network actions are disabled');
   if(request.service==='get_usage_history'){const match=request.service_data?.entity_id?.match(/_client_client(\d+)_/);return {response:history(request.service_data?.resolution,match?clientScale(Number(match[1])):1)};}
   throw Error('Unknown demo service');
  },callService:async()=>{throw new Error('Demo mode: network actions are disabled');}};
}
function update(){panel.hass=build();}
panel.panel={config:{map_path:'/google-wifi-insights/mapa'}};
panel.route={path:parameters.get('view')==='locations'?'/locations':parameters.get('view')==='map'?'/mapa':parameters.get('view')==='management'?'/management':'/overview'};
document.querySelector('#language').addEventListener('change',update);
document.querySelector('#scenario').addEventListener('change',update);
document.querySelector('#theme').addEventListener('change',update);
document.addEventListener('hass-more-info',event=>{
  document.querySelector('#detail-text').textContent=JSON.stringify(entities[event.detail.entityId]||{demo:true},null,2);
  document.querySelector('#details').showModal();
});
update();
if(!capture)setInterval(()=>{tick++;update();},3000);
