import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {JSDOM} from 'jsdom';
import {languageOf,mapModel,operationFeedback} from '../www/gwi-map-model.js';

const source=await readFile(new URL('../www/gwi-management.js',import.meta.url),'utf8');
const settle=()=>new Promise(resolve=>setImmediate(resolve));
function data(scope='entry:one'){
 return {scope,network_id:scope.split(':').at(-1),name:scope,entity_id:'sensor.'+scope.replace(':','_'),areas:[{id:'office',name:'Example office'},{id:'studio',name:'Example studio'}],points:[{id:'point',name:'Example point',entity_id:'sensor.'+scope.replace(':','_')+'_point',area_id:null,online:true,is_root:false}],name_candidates:[{station_id:'client',google_name:'Unnamed device',proposed_name:'Example phone',mac_address:'02:00:00:00:00:01'}],rename:{writable:false,state:'request_schema_unverified'}};
}
function fixture(){
 const states={};
 for(const scope of ['entry:one','entry:two']){
  const entity_id='sensor.'+scope.replace(':','_');
  states[entity_id]={state:'quality_data_available',attributes:{gwi_scope:scope,gwi_network_id:scope.split(':').at(-1),gwi_kind:'network',gwi_metric:'diagnosis',device_name:scope,data_source:'google_cloud'}};
  states[entity_id+'_point']={state:'0',attributes:{gwi_scope:scope,gwi_kind:'point',gwi_metric:'clients',gwi_item_id:'point',device_name:'Example point',online:true}};
 }
 return {language:'en',user:{is_admin:true},states};
}
function environment(handler){
 const dom=new JSDOM('<main></main>',{url:'http://ha.example/google-wifi-insights/management',pretendToBeVisual:true});
 const calls=[],copied=[];
 const context=vm.createContext({HTMLElement:dom.window.HTMLElement,document:dom.window.document,customElements:dom.window.customElements,languageOf,mapModel,operationFeedback,navigator:{clipboard:{writeText:async value=>copied.push(value)}}});
 vm.runInContext(source.replace(/^import[^\n]*\n/gm,'').replace(/^export /gm,''),context);
 const card=dom.window.document.createElement('google-wifi-management');dom.window.document.querySelector('main').append(card);
 const hass={...fixture(),callWS:async request=>{calls.push(request);return {response:await (handler?handler(request):data(request.service_data.entity_id==='sensor.entry_two'?'entry:two':'entry:one'))};}};
 card.hass=hass;
 return {dom,card,root:card.shadowRoot,hass,calls,copied};
}
function click(root,text){const b=[...root.querySelectorAll('button')].find(b=>b.textContent===text);assert.ok(b,'Button exists: '+text);b.click();return b;}

test('management loads cached data once and retains drafts, focus and scroll during HA updates',async()=>{
 const {card,root,hass,calls}=environment();await settle();
 const select=root.querySelector('select[data-point]');select.value='studio';select.dispatchEvent(new select.ownerDocument.defaultView.Event('change'));select.focus();
 const section=root.querySelector('section');section.scrollTop=125;
 for(let i=0;i<200;i++)card.hass={...hass};
 assert.equal(calls.length,1);assert.equal(calls[0].service,'get_management');
 assert.equal(root.querySelector('select[data-point]'),select);assert.equal(select.value,'studio');assert.equal(root.activeElement,select);assert.equal(section.scrollTop,125);
 assert.match(root.textContent,/does not change the fixed device area/);
 click(root,'Refresh view');await settle();assert.equal(root.querySelector('select[data-point]').value,'studio');
});

test('saving an area calls the verified point service and allows clearing it',async()=>{
 const {root,calls}=environment(request=>{
  const value=data();if(request.service==='set_point_area')value.points[0].area_id=request.service_data.area_id;return value;
 });await settle();
 const select=root.querySelector('select[data-point]');select.value='office';click(root,'Save area');await settle();
 assert.equal(calls[1].service,'set_point_area');assert.equal(calls[1].service_data.entity_id,'sensor.entry_one_point');assert.equal(calls[1].service_data.area_id,'office');
 assert.match(root.querySelector('[role=status]').textContent,/saved/);
 root.querySelector('select[data-point]').value='';click(root,'Save area');await settle();assert.equal(calls[2].service_data.area_id,null);
});

test('actions show exact target and network and send only after explicit confirmation',async()=>{
 const {root,calls,card}=environment(request=>request.service==='google_action'?{state:'CREATED'}:data());await settle();
 click(root,'Restart point');assert.equal(calls.length,1);assert.match(root.querySelector('.confirmation').textContent,/Example point.*entry:one/);
 click(root,'Cancel');assert.equal(calls.length,1);
 click(root,'Restart point');click(root,'Confirm request');await settle();
 assert.equal(calls[1].service,'google_action');assert.equal(calls[1].service_data.action,'restart_point');assert.equal(calls[1].service_data.entity_id,'sensor.entry_one_point');assert.match(root.querySelector('[role=status]').textContent,/Completion is not yet confirmed/);
 card._confirm({id:'one',name:'Network',entity_id:'sensor.entry_one',kind:'network'},'restart_network');click(root,'Confirm request');await settle();assert.equal(calls[2].service_data.entity_id,'sensor.entry_one');
});

test('an uncertain action is never labelled complete or automatically repeated',async()=>{
 const {root,hass,card,calls}=environment(request=>request.service==='google_action'?Promise.reject(Error('Delivery unknown')):data());await settle();
 click(root,'Test mesh to primary');click(root,'Confirm request');await settle();assert.match(root.querySelector('[role=status]').textContent,/delivery is unconfirmed/);
 for(let i=0;i<50;i++)card.hass=hass;
 assert.equal(calls.filter(c=>c.service==='google_action').length,1);
});

test('late responses from a previous network cannot change the selected network',async()=>{
 let release;const {root,calls}=environment(request=>request.service_data.entity_id==='sensor.entry_one'?new Promise(resolve=>{release=resolve;}):data('entry:two'));
 const select=root.querySelector('.toolbar select');select.value='entry:two';select.dispatchEvent(new select.ownerDocument.defaultView.Event('change'));await settle();
 assert.equal(calls.length,2);release(data());await settle();assert.equal(select.value,'entry:two');
 click(root,'Restart point');click(root,'Confirm request');await settle();assert.equal(calls.at(-1).service_data.entity_id,'sensor.entry_two_point');
});

test('non-administrators cannot load management and unavailable networks cannot write',async()=>{
 const {root,card,hass,calls}=environment();await settle();const count=calls.length;
 card.hass={...hass,user:{is_admin:false}};assert.match(root.textContent,/administrator is required/);assert.equal(root.querySelectorAll('button[data-write]').length,0);
 assert.equal(calls.length,count);
 card.hass={...hass,states:Object.fromEntries(Object.entries(hass.states).map(([id,state])=>[id,{...state,state:'unavailable'}]))};
 await settle();assert.match(root.textContent,/network is unavailable/);assert.equal(calls.length,count+1);
 assert.equal(calls.at(-1).service,'get_management');assert.ok([...root.querySelectorAll('button[data-write]')].every(b=>b.disabled));
});

test('name suggestions remain read-only, escape provider text and copy only the selected name',async()=>{
 const {root,calls,copied}=environment(()=>{const d=data();d.name_candidates[0].proposed_name='<img src=x onerror=bad>';return d;});await settle();
 assert.equal(root.querySelector('img'),null);assert.match(root.textContent,/Automatic naming starts disabled/);
 click(root,'Copy suggested name');await settle();assert.deepEqual(copied,['<img src=x onerror=bad>']);assert.equal(calls.length,1);
 assert.ok(root.querySelector('.candidate input').readOnly);
});

test('failed loads wait for a manual retry and language follows Home Assistant',async()=>{
 let failed=true;const {root,card,hass,calls}=environment(()=>{if(failed)throw Error('No response');return data();});await settle();
 for(let i=0;i<50;i++)card.hass=hass;
 assert.equal(calls.length,1);assert.match(root.textContent,/Management is unavailable/);
 failed=false;click(root,'Refresh view');await settle();card.hass={...hass,language:'pt-PT'};
 assert.equal(root.querySelector('h1').textContent,'Gestão da rede');assert.match(root.textContent,/Guardar divisão/);assert.equal(calls.length,2);
});

test('operation status follows HA without replacing open controls',async()=>{
 const {root,card,hass}=environment();await settle();const select=root.querySelector('select[data-point]');
 const status={state:'running',attributes:{gwi_scope:'entry:one',gwi_kind:'point',gwi_item_id:'point',gwi_metric:'operation_status',operation_feedback:{phase:'running',action:'test_mesh'}}};
 card.hass={...hass,states:{...hass.states,'sensor.operation':status}};
 assert.equal(root.querySelector('select[data-point]'),select);assert.match(root.querySelector('.action-target:last-child .feedback').textContent,/Running/);
 assert.equal(root.querySelector('[data-action=test_mesh]').disabled,true);
});

test('automatic naming starts only after confirmation of the selected network',async()=>{
 const {root,calls}=environment(request=>{const d=data();d.rename={writable:true,enabled:request.service==='set_name_sync'?request.service_data.enabled:false,history:[]};return d;});await settle();
 click(root,'Enable automatic naming');assert.equal(calls.length,1);assert.match(root.querySelector('.confirmation').textContent,/entry:one/);
 click(root,'Confirm request');await settle();assert.equal(calls[1].service,'set_name_sync');assert.equal(calls[1].service_data.enabled,true);
 click(root,'Disable automatic naming');await settle();assert.equal(calls[2].service_data.enabled,false);
});

test('a selected suggestion sends only the frozen preview and no arbitrary replacement name',async()=>{
 const {root,calls,hass,card}=environment(request=>{const d=data();d.name_candidates[0].entity_id='sensor.client';d.rename={writable:true,enabled:false,history:[]};if(request.service==='rename_client'){d.name_candidates=[];d.name_result={state:'verified'};}return d;});
 hass.states['sensor.client']={state:'Example point',attributes:{google_name:'Unnamed device'}};await settle();card.hass={...hass};
 click(root,'Apply name in Google');assert.equal(calls.length,1);click(root,'Confirm request');await settle();
 assert.equal(calls[1].service,'rename_client');assert.deepEqual({...calls[1].service_data},{entity_id:'sensor.client',expected_google_name:'Unnamed device',expected_mac:'02:00:00:00:00:01',expected_ha_name:'Example phone'});
 assert.match(root.querySelector('[role=status]').textContent,/verified in Google/);
});

test('an unconfirmed name change offers read-only verification and is never resent',async()=>{
 const {root,calls,hass,card}=environment(request=>{const d=data();d.rename={writable:true,enabled:true,paused_reason:'delivery_or_readback_unconfirmed',history:[{request_id:'request',old_name:'Unnamed Device',new_name:'Example phone',state:'unconfirmed',kind:'rename'}]};if(request.service==='verify_name')d.name_result={state:'unconfirmed'};return d;});await settle();
 click(root,'Verify result');await settle();assert.equal(calls[1].service,'verify_name');assert.match(root.querySelector('[role=status]').textContent,/not be repeated automatically/);
 for(let i=0;i<50;i++)card.hass=hass;
 assert.equal(calls.filter(c=>c.service==='rename_client').length,0);
});

test('a verified name change needs a separate confirmation to undo',async()=>{
 const {root,calls}=environment(()=>{const d=data();d.rename={writable:true,enabled:false,history:[{request_id:'request',old_name:'Unnamed Device',new_name:'Example phone',state:'verified',kind:'rename'}]};d.name_result={state:'verified'};return d;});await settle();
 click(root,'Undo name change');assert.equal(calls.length,1);assert.match(root.querySelector('.confirmation').textContent,/Example phone → Unnamed Device/);
 click(root,'Confirm request');await settle();assert.equal(calls[1].service,'undo_name');assert.equal(calls[1].service_data.request_id,'request');
});

test('automatic naming can be disabled while paused and the network is unavailable',async()=>{
 const {root,card,hass,calls}=environment(request=>{const d=data();d.rename={writable:true,enabled:request.service!=='set_name_sync',paused_reason:'delivery_or_readback_unconfirmed',history:[]};return d;});await settle();
 card.hass={...hass,states:Object.fromEntries(Object.entries(hass.states).map(([id,state])=>[id,{...state,state:'unavailable'}]))};
 const disable=[...root.querySelectorAll('button')].find(b=>b.textContent==='Disable automatic naming');assert.equal(disable.disabled,false);disable.click();await settle();
 assert.equal(calls.at(-1).service,'set_name_sync');assert.equal(calls.at(-1).service_data.enabled,false);
});

test('an undone client explains its automatic exclusion and does not offer the obsolete undo',async()=>{
 const {root,calls}=environment(()=>{const d=data();d.rename={writable:true,enabled:true,excluded_station_ids:['client'],history:[{request_id:'rename',station_id:'client',old_name:'Unnamed Device',new_name:'Example phone',state:'verified',kind:'rename'},{request_id:'undo',station_id:'client',old_name:'Example phone',new_name:'Unnamed Device',state:'verified',kind:'undo'}]};return d;});await settle();
 assert.match(root.textContent,/Excluded from automatic naming after undo/);
 assert.equal([...root.querySelectorAll('button')].some(b=>b.textContent==='Undo name change'),false);
 assert.ok([...root.querySelectorAll('button')].some(b=>b.textContent==='Apply name in Google'));
 assert.equal(calls.length,1);
});
