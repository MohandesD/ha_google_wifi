import test from 'node:test';
import assert from 'node:assert/strict';
import {pointInformation,networkInformation,firmwareSummary} from '../www/gwi-information.js';
import {mapModel} from '../www/gwi-map-model.js';

test('firmware views label historical versions, preserve false and raw progress, and escape text',()=>{
 const point={firmwareInfo:{installed_version:'14000.1.2',update_status:'idle',update_required:false,update_progress_raw:0.25,
  release_notes:{queried_version:'14000.1.2',matching_installed:false,notes:[{version:'13000.1.0',title:'<img onerror="bad">',description:'Old note <script>bad</script>'}]}}};
 const en=pointInformation(point,'en'),pt=pointInformation(point,'pt');
 assert.match(en,/historical notes/);assert.match(en,/13000\.1\.0/);assert.match(en,/>No<\/dd>/);
 assert.match(en,/0\.25/);assert.doesNotMatch(en,/>25%/);assert.doesNotMatch(en,/<script>|<img/);
 assert.match(pt,/notas históricas/);assert.match(pt,/Atualização necessária/);
 assert.equal(firmwareSummary(point,'pt'),'14000.1.2 · Em espera');
});

test('LAN/WAN view renders IPv6 false and all supplied information without inferred values',()=>{
 const html=networkInformation({networkInfo:{cloud:{wan_properties:{wanMode:'STATIC',ipAddress:'198.51.100.1'},
  wan_settings:{ipv6Enabled:false},lan_settings:{dhcpPoolBegin:'10.7.0.5',upnpEnabled:true}},newField:'kept'}},'en');
 assert.match(html,/198\.51\.100\.1/);assert.match(html,/10\.7\.0\.5/);assert.match(html,/>No<\/dd>/);
 assert.match(html,/newField/);assert.match(html,/Not supplied/);
});

test('information from native diagnostic sensors is scoped to its network and point',()=>{
 const states={
  'sensor.p':{state:'0',attributes:{gwi_scope:'first',gwi_kind:'point',gwi_metric:'clients',gwi_item_id:'p',device_name:'Point'}},
  'sensor.other':{state:'0',attributes:{gwi_scope:'second',gwi_kind:'point',gwi_metric:'clients',gwi_item_id:'p',device_name:'Other'}},
  'sensor.info':{state:'idle',attributes:{gwi_scope:'first',gwi_kind:'point',gwi_metric:'update_status',gwi_item_id:'p',firmware_information:{installed_version:'14000.1.2'}}},
  'sensor.network':{state:'available',attributes:{gwi_scope:'first',gwi_kind:'network',gwi_metric:'network_information_status',network_information:{cloud:{wan_properties:{wanMode:'STATIC'}}}}},
 };
 const networks=mapModel(states,{},'en');
 assert.equal(networks.find(n=>n.scope==='first').points[0].firmwareInfo.installed_version,'14000.1.2');
 assert.equal(networks.find(n=>n.scope==='second').points[0].firmwareInfo,undefined);
 assert.equal(networks.find(n=>n.scope==='first').networkInfo.cloud.wan_properties.wanMode,'STATIC');
});
