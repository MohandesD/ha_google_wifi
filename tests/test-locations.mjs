import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {JSDOM} from 'jsdom';
import * as model from '../www/gwi-map-model.js';

const source=await readFile(new URL('../www/gwi-locations.js',import.meta.url),'utf8');
const panelSource=await readFile(new URL('../custom_components/google_wifi_insights/frontend/google-wifi-insights-panel.js',import.meta.url),'utf8');
const settle=()=>new Promise(resolve=>setTimeout(resolve,0));
function fixture(){
 const states={};
 for(const [scope,source,location,name]of [['local','local_status','home','Example LAN'],['first','google_cloud','home','Example WiFi'],['second','google_cloud','remote','Example WiFi'],['unassigned','google_cloud',null,'Unassigned WiFi']]){
  const attributes={gwi_scope:scope,gwi_network_id:'same-id',gwi_item_id:'same-id',gwi_kind:'network',gwi_metric:'diagnosis',data_source:source,device_name:name,network_location_id:location,network_location:location==='home'?'Example home':location==='remote'?'Example remote':null};
  states['sensor.'+scope]={state:'insufficient_radio_data',attributes};
  states['sensor.'+scope+'_point']={state:source==='local_status'?'unknown':'1',attributes:{...attributes,gwi_kind:'point',gwi_item_id:'same-point',gwi_metric:'clients',device_name:'Same point name',online:true}};
  if(source==='google_cloud')states['sensor.'+scope+'_client']={state:'Same point name',attributes:{...attributes,gwi_kind:'client',gwi_item_id:'same-client',gwi_metric:'point',device_name:'Example device',connected:true,ap_id:'same-point'}};
 }
 return {language:'en',user:{is_admin:true},states,services:{google_wifi_insights:{set_network_location:{}}}};
}
function environment(handler){
 const dom=new JSDOM('<main></main>',{url:'http://ha.example/google-wifi-insights/locations',runScripts:'outside-only',pretendToBeVisual:true});
 const context=dom.getInternalVMContext();Object.assign(context,model);
 vm.runInContext(source.replace(/^import[^\n]*\n/gm,'').replace(/^export /gm,''),context);
 const card=dom.window.document.createElement('google-wifi-locations');dom.window.document.querySelector('main').append(card);
 const calls=[],hass={...fixture(),callWS:async request=>{calls.push(request);return {response:handler?await handler(request):{scope:request.service_data.entity_id.replace('sensor.',''),location:request.service_data.name?{id:'saved',name:request.service_data.name}:null}};}};
 card.hass=hass;return {dom,card,root:card.shadowRoot,hass,calls};
}
const cardFor=(root,scope)=>[...root.querySelectorAll('.network')].find(c=>c.dataset.scope===scope);
const click=(card,text)=>{const b=[...card.querySelectorAll('button')].find(b=>b.textContent===text);assert.ok(b,text);b.click();return b;};

test('local status has actionable setup, cloud accounts are distinguished, and opening locations sends no requests',()=>{
 const {root,calls}=environment();
 assert.equal(root.querySelectorAll('.network').length,4);assert.equal(calls.length,0);
 assert.match(cardFor(root,'local').textContent,/data limitation, not a pending Google validation/);
 assert.match(cardFor(root,'first').textContent,/already supplied by a linked Google account/);
 assert.equal(root.querySelectorAll('details li').length,4);
 assert.match(root.querySelector('details').textContent,/Renew Google authentication/);
 assert.equal(root.querySelector('a[href^="/config"]').getAttribute('href'),'/config/integrations/integration/google_wifi_insights');
 const external=root.querySelector('a[target=_blank]');assert.match(external.rel,/noopener/);
 const guide=root.querySelector('details');guide.querySelector('summary').click();assert.equal(guide.open,false);click(cardFor(root,'local'),'Open connection steps');assert.equal(guide.open,true);assert.equal(root.activeElement,guide.querySelector('summary'));
 assert.doesNotMatch(root.textContent,/Client associations require validation/);
});

test('location labels are saved only for the selected network and can be cleared without enabling naming',async()=>{
 const {root,calls}=environment(),card=cardFor(root,'second'),input=card.querySelector('input');input.value='Workshop';input.dispatchEvent(new input.ownerDocument.defaultView.Event('input'));
 click(card,'Save location');await settle();
 assert.equal(calls.length,1);assert.equal(calls[0].service,'set_network_location');assert.deepEqual({...calls[0].service_data},{entity_id:'sensor.second',name:'Workshop'});
 assert.equal(input.value,'Workshop');assert.match(card.querySelector('[role=status]').textContent,/saved/);
 click(card,'Clear location');await settle();assert.equal(calls[1].service_data.name,null);assert.equal(input.value,'');
 assert.equal(cardFor(root,'first').querySelector('input').value,'Example home');
});

test('drafts, input focus, native disclosure state and scroll survive ordinary HA updates',()=>{
 const {root,card,hass,dom}=environment(),row=cardFor(root,'local'),input=row.querySelector('input');input.value='Draft home';input.dispatchEvent(new dom.window.Event('input'));input.focus();row.scrollTop=120;
 const guide=root.querySelector('details');guide.open=false;
 for(let i=0;i<100;i++)card.hass={...hass};
 assert.equal(cardFor(root,'local'),row);assert.equal(row.querySelector('input'),input);assert.equal(input.value,'Draft home');assert.equal(root.activeElement,input);assert.equal(row.scrollTop,120);assert.equal(guide.open,false);
 assert.equal(root.querySelectorAll('datalist option').length,2);
});

test('nonadmins and older backends keep read-only setup guidance',()=>{
 const {root,card,hass,calls}=environment();card.hass={...hass,user:{is_admin:false}};
 assert.ok([...root.querySelectorAll('input')].every(n=>n.disabled));assert.ok([...root.querySelectorAll('.primary')].every(n=>n.disabled));assert.match(root.textContent,/administrator can edit/);
 card.hass={...hass,services:{}};assert.match(root.textContent,/Update the integration/);assert.ok([...root.querySelectorAll('.primary')].every(n=>n.disabled));assert.equal(calls.length,0);
 assert.ok(root.querySelector('a[href^="/config"]'));
});

test('outage labels are editable but no client count or authentication success is invented',async()=>{
 const {root,card,hass,calls}=environment();const states=structuredClone(hass.states);states['sensor.second'].state='unavailable';card.hass={...hass,states};
 const row=cardFor(root,'second');assert.match(row.textContent,/Network query unavailable/);assert.match(row.textContent,/authentication repair or connection error/);assert.equal(row.querySelector('.primary').disabled,false);
 click(row,'Save location');await settle();assert.equal(calls.length,1);assert.equal(calls[0].service,'set_network_location');
 assert.equal(states['sensor.second'].state,'unavailable');
});

test('uncertain saves are not automatically repeated and late responses cannot rewrite another network',async()=>{
 let release;const {root,card,hass,calls}=environment(()=>new Promise(resolve=>{release=resolve;}));const row=cardFor(root,'second');click(row,'Save location');
 const states={...hass.states};for(const key of Object.keys(states))if(key.startsWith('sensor.second'))delete states[key];card.hass={...hass,states};
 release({scope:'second',location:{id:'saved',name:'Old reply'}});await settle();assert.equal(cardFor(root,'second'),undefined);assert.equal(cardFor(root,'first').querySelector('input').value,'Example home');assert.equal(calls.length,1);
 const env=environment(()=>{throw Error('No delivery confirmation');});click(cardFor(env.root,'local'),'Save location');await settle();assert.match(cardFor(env.root,'local').textContent,/Could not save/);for(let i=0;i<50;i++)env.card.hass=env.hass;assert.equal(env.calls.length,1);
});

test('provider labels are escaped, invalid drafts are rejected, and language follows HA',async()=>{
 const {root,card,hass,calls}=environment();const states=structuredClone(hass.states);states['sensor.second'].attributes.device_name='<img src=x onerror=bad>';card.hass={...hass,states};assert.equal(root.querySelector('img'),null);
 const row=cardFor(root,'second');row.querySelector('input').value='a'.repeat(65);click(row,'Save location');await settle();assert.equal(calls.length,0);assert.match(row.textContent,/64 characters/);
 card.hass={...hass,language:'pt-PT'};assert.equal(root.querySelector('h1').textContent,'Localizações e configuração da ligação');assert.match(root.textContent,/não uma validação Google pendente/);
});

for(const response of [{scope:'wrong',location:null},{scope:'second'},{scope:'second',location:false},{scope:'second',location:{id:4,name:'Bad reply'}}]){
 test('a mismatched or malformed location response is never shown as saved: '+JSON.stringify(response),async()=>{
  const {root,calls}=environment(()=>response),row=cardFor(root,'second');click(row,'Save location');await settle();assert.match(row.querySelector('[role=status]').textContent,/Could not save/);assert.equal(calls.length,1);
 });
}

test('location filters never merge repeated point IDs, names or clients from separate homes',()=>{
 const states=fixture().states,home=model.mapModel(states,{location_id:'home'}),remote=model.mapModel(states,{location_id:'remote'});
 assert.equal(home.length,2);assert.equal(remote.length,1);assert.equal(remote[0].scope,'second');assert.equal(home.find(n=>n.source==='local_status').clients.length,0);
 assert.equal(remote[0].points[0].clients[0].entityId,'sensor.second_client');
 assert.equal(model.mapModel(states,{location_id:'unassigned'})[0].scope,'unassigned');
 assert.equal(model.mapModel(states,{location_id:'home',network_entity:'sensor.second'}).length,0);
});

function panelEnvironment(){
 const dom=new JSDOM('<main></main>',{url:'http://ha.example/google-wifi-insights/overview',runScripts:'outside-only'}),context=dom.getInternalVMContext();Object.assign(context,model);
 for(const tag of ['google-wifi-dashboard-ui','google-wifi-insights-map','google-wifi-management','google-wifi-locations']){
  dom.window.customElements.define(tag,class extends dom.window.HTMLElement{setConfig(value){this.config=value;}set hass(value){this.lastHass=value;}});
 }
 vm.runInContext(panelSource.replace(/^import[^\n]*\n/gm,''),context);
 const panel=dom.window.document.createElement('google-wifi-insights-panel');dom.window.document.querySelector('main').append(panel);panel._hass=fixture();panel._update();
 const change=(key,value)=>{panel._selectors[key].value=value;panel._selectors[key].dispatchEvent(new dom.window.Event('change'));};
 return {panel,change};
}

test('shared panel filters all views to the chosen home/network while locations remains an inventory',()=>{
 const {panel,change}=panelEnvironment();
 change('location','remote');assert.equal(panel._selectors.network.options.length,2);change('network','second');
 for(const view of ['overview','map','management']){assert.equal(panel._cards[view].config.location_id,'remote');assert.equal(panel._cards[view].config.network_entity,'sensor.second');}
 assert.equal(panel._cards.map.config.locations_path,'/google-wifi-insights/locations');
 panel.route={path:'/locations'};assert.equal(panel._main.firstChild,panel._cards.locations);assert.equal(panel._filters.hidden,true);assert.equal(panel._cards.locations.config.location_id,undefined);
 change('location','home');assert.equal(panel._cards.overview.config.network_entity,undefined);assert.equal(panel._selectors.network.options.length,3);
 assert.equal(panel._cards.management.config.location_id,'home');
});

test('management uses one explicit shared cloud network and preserves a selected home',()=>{
 const {panel,change}=panelEnvironment();
 change('location','remote');change('network','second');panel.route={path:'/management'};
 assert.equal(panel._selectors.network.options.length,1);assert.equal(panel._selectors.network.value,'second');
 assert.equal(panel._cards.management.config.network_entity,'sensor.second');assert.equal(panel._cards.management.config.hide_network_selector,true);
 change('location','home');assert.equal(panel._selectors.network.options.length,1);assert.equal(panel._selectors.network.value,'first');
 assert.equal(panel._cards.management.config.network_entity,'sensor.first');
 panel.route={path:'/overview'};assert.equal(panel._selectors.network.options.length,3);
 change('network','local');panel.route={path:'/management'};
 assert.equal(panel._selectors.network.value,'first','A local-status row is not a management target');
 change('location','');change('network','second');
 panel._hass.states['sensor.second'].state='unavailable';panel._update();
 assert.equal(panel._selectors.network.value,'second','An outage never silently switches actions to another home');
});

test('a local-only selected location never falls back to a cloud network in another home',()=>{
 const {panel,change}=panelEnvironment();change('location','home');
 for(const key of Object.keys(panel._hass.states))if(key.startsWith('sensor.first'))delete panel._hass.states[key];
 panel.route={path:'/management'};
 assert.equal(panel._selectors.network.options.length,0);assert.equal(panel._cards.management.config.network_entity,undefined);
 assert.equal(model.mapModel(panel._hass.states,panel._cards.management.config).filter(n=>n.source==='google_cloud').length,0);
});
