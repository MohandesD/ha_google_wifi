import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {informationCss} from '../www/gwi-information.js';
import {languageOf,translate,mapModel,isLocalHaPath,overviewPath,operationFeedback} from '../www/gwi-map-model.js';

test('effective HA language wins over browser defaults and handles regional variants',()=>{
  assert.equal(languageOf({language:'en-GB',locale:{language:'pt'}}),'en');
  assert.equal(languageOf({locale:{language:'pt-BR'}}),'pt');
  assert.equal(languageOf('pt_PT'),'pt');
  assert.equal(languageOf(undefined),'en');
  assert.equal(languageOf('unsupported'),'en');
  assert.equal(translate('en')('weak_clients',{count:1}),'1 weak connection observed');
  assert.equal(translate('pt')('weak_clients',{count:0}),'0 ligações fracas observadas');
});

const source=await readFile(new URL('../www/google-wifi-insights-map.js',import.meta.url),'utf8');
function cardEnvironment(config={},timers={}) {
  const consumers=new Map(),disposed=[];
  class Node {
    children=[]; listeners=new Map();
    constructor(tag='host'){this.tag=tag;this.dataset={};this.classList={add(){}};this.ownerDocument={scrollingElement:null};}
    querySelectorAll(){return [];}
    getRootNode(){return {host:null};}
    set textContent(value){this.text=String(value);}
    get textContent(){return (this.text||'')+this.children.map(x=>x.textContent||'').join(' ');}
    append(...nodes){this.children.push(...nodes);}
    replaceChildren(...nodes){this.children=[...nodes];}
    attachShadow(){return this.shadowRoot=new Node('shadow');}
    setAttribute(){}
    addEventListener(type,listener){this.listeners.set(type,listener);}
    dispatchEvent(event){
      if(event.type==='context-request'){
        consumers.set(event.context,event.callback);
        const value=event.context==='states'?{}:event.context==='hassInternationalization'?{language:'en'}:{language:'en'};
        event.callback(value,()=>disposed.push(event.context));
      }
      return true;
    }
  }
  const elements=new Map();
  const context=vm.createContext({mapModel,translate,languageOf,isLocalHaPath,overviewPath,operationFeedback,informationCss,formatBytes:value=>value==null?'—':String(value)+' B',
    HTMLElement:Node,document:{createElement:tag=>new Node(tag),createElementNS:(_,tag)=>new Node(tag),createTextNode:text=>{const n=new Node();n.textContent=text;return n;}},
    CustomEvent:class{constructor(type,options){this.type=type;Object.assign(this,options);}},
    ResizeObserver:class{observe(){}disconnect(){}},requestAnimationFrame:()=>1,cancelAnimationFrame(){},
    customElements:{get:name=>elements.get(name),define:(name,value)=>elements.set(name,value)},window:{customCards:[]},
    ...timers,
  });
  vm.runInContext(source.replace(/^(?:import[^\n]*\n)+/,''),context);
  const card=new (elements.get('google-wifi-insights-map'))(); card.setConfig(config); card.connectedCallback();
  return {card,consumers,disposed};
}

test('context language updates the card with unchanged states and preserves expansion',()=>{
  const {card,consumers,disposed}=cardEnvironment();
  assert.match(card.shadowRoot.textContent,/WiFi network map/);
  card._expanded.add('home:point');
  consumers.get('hassInternationalization')({language:'pt-PT'});
  assert.match(card.shadowRoot.textContent,/Mapa da rede WiFi/);
  assert.equal(card.lang,'pt');
  assert.equal(card._expanded.has('home:point'),true);
  consumers.get('hassInternationalization')({language:'en'});
  assert.match(card.shadowRoot.textContent,/WiFi network map/);
  card.disconnectedCallback();
  assert.equal(disposed.length,4);
});

test('legacy hass updates language and user-provided titles survive a language change',()=>{
  const {card}=cardEnvironment({title:'My own network'});
  card.hass={states:{},locale:{language:'pt-BR'}};
  assert.match(card.shadowRoot.textContent,/My own network/);
  assert.match(card.shadowRoot.textContent,/Dispositivos por ponto/);
  card.hass={states:{},language:'en'};
  assert.match(card.shadowRoot.textContent,/Devices by point/);
  card.setConfig({title:'Updated network title'});
  assert.match(card.shadowRoot.textContent,/Updated network title/);
});

test('rendered client contains measured RSSI, roaming link and separate Google rating',()=>{
  const {card}=cardEnvironment();
  card.hass={language:'pt',states:{
    'sensor.point':{state:'1',attributes:{gwi_scope:'home',gwi_kind:'point',gwi_metric:'clients',gwi_item_id:'p',device_name:'Study',online:true,is_root:true,root_ap_id:'p',data_source:'google_cloud'}},
    'sensor.shelly':{state:'Study',attributes:{gwi_scope:'home',gwi_kind:'client',gwi_metric:'point',gwi_item_id:'s',device_name:'Shelly',connected:true,ap_id:'p',rssi:-72,rssi_source:'shelly_wifi_status',roaming_supported:true,radio_available:true,gwi_device_id:'own',signal_quality:'excellent',quality_source:'google_connection_rating'}},
  }};
  assert.match(card.shadowRoot.textContent,/-72 dBm/);
  assert.match(card.shadowRoot.textContent,/RSSI medido pelo Shelly/);
  assert.match(card.shadowRoot.textContent,/Qualidade Google · Excelente/);
  assert.match(card.shadowRoot.textContent,/Controlos de roaming/);
});

test('HA state bursts are coalesced and render the latest state once',()=>{
  const jobs=[];
  const {card,consumers}=cardEnvironment({}, {setTimeout:callback=>{jobs.push(callback);return jobs.length;},clearTimeout(){}});
  for(let count=1;count<=30;count++)consumers.get('states')({'sensor.point':{state:String(count),attributes:{gwi_scope:'home',gwi_kind:'point',gwi_metric:'clients',gwi_item_id:'p',device_name:'Point',online:true,data_source:'google_cloud'}}});
  assert.equal(jobs.length,1);
  jobs[0]();
  assert.equal(card._model[0].points[0].count,30);
  card.disconnectedCallback();
});

test('standalone map provides a localized return link for a configured dashboard',()=>{
  const {card}=cardEnvironment({overview_path:'/my-wifi/status'});
  const link=()=>card.shadowRoot.children[1].children[0].children[0];
  assert.equal(link().tag,'a');
  assert.equal(link().href,'/my-wifi/status');
  assert.match(link().textContent,/Back to overview/);
  card.hass={states:{},language:'pt-PT'};
  assert.match(link().textContent,/Voltar à visão geral/);
  for(const path of ['https://example.invalid','//example.invalid','/\\example.invalid'])
    assert.throws(()=>card.setConfig({overview_path:path}),/overview_path/);
});

test('automatic return paths stay within the current HA panel',()=>{
  assert.equal(overviewPath({},'/my-wifi/mapa'),'/my-wifi/overview');
  assert.equal(overviewPath({},'/my-wifi/diagnostics/'),'/my-wifi/overview');
  assert.equal(overviewPath({overview_path:'/custom-dashboard/status'},'/my-wifi/mapa'),'/custom-dashboard/status');
  assert.equal(overviewPath({},'/my-wifi/unrelated'),null);
  assert.equal(overviewPath({overview_path:'//example.invalid'}),null);
});

test('local map explains missing client inventory and links to scoped setup steps',()=>{
  const {card}=cardEnvironment({locations_path:'/alternate-wifi/locations'});
  card.hass={language:'en',states:{'sensor.local':{state:'insufficient_radio_data',attributes:{gwi_kind:'network',gwi_metric:'diagnosis',gwi_scope:'local',data_source:'local_status',device_name:'Example LAN'}},'sensor.point':{state:'unknown',attributes:{gwi_kind:'point',gwi_metric:'clients',gwi_item_id:'point',gwi_scope:'local',data_source:'local_status',device_name:'Example point',online:true}}}};
  assert.match(card.shadowRoot.textContent,/Local status does not include connected devices/);
  assert.doesNotMatch(card.shadowRoot.textContent,/require validation/);
  const all=[];function visit(n){all.push(n);for(const c of n.children||[])visit(c);}visit(card.shadowRoot);
  assert.equal(all.find(n=>n.tag==='a'&&n.textContent.includes('See connection steps')).href,'/alternate-wifi/locations');
  assert.throws(()=>card.setConfig({locations_path:'https://example.invalid'}));
});

test('rendered restart feedback follows Google states and belongs to its own control',()=>{
  const {card}=cardEnvironment();
  const states={
    'sensor.point':{state:'0',attributes:{gwi_scope:'test',gwi_kind:'point',gwi_metric:'clients',gwi_item_id:'p',device_name:'Test point',online:true,data_source:'google_cloud'}},
    'button.restart':{state:'2026-10-13T12:00:00Z',attributes:{gwi_scope:'test',gwi_kind:'point',gwi_metric:'restart_point',gwi_item_id:'p',friendly_name:'Restart point'}},
    'sensor.status':{state:'accepted',attributes:{gwi_scope:'test',gwi_kind:'network',gwi_metric:'operation_status'}},
  };
  const feedback={request_id:'request',action:'restart_point',target_kind:'point',target_id:'p',target_name:'Test point',phase:'accepted',state:'CREATED',updated_at:'2026-10-13T12:00:00Z'};
  states['button.restart'].attributes.operation_feedback=feedback;
  states['sensor.status'].attributes.operation_feedback=feedback;
  card.hass={language:'en',states};
  assert.match(card.shadowRoot.textContent,/Request accepted/);
  assert.doesNotMatch(card.shadowRoot.textContent,/Running|Completed/);
  feedback.phase='running';feedback.state='RUNNING';card.hass={language:'pt',states};
  assert.match(card.shadowRoot.textContent,/Em execução/);
  feedback.phase='completed';feedback.state='DONE';card.hass={language:'pt',states};
  assert.match(card.shadowRoot.textContent,/Concluído/);
  assert.equal(operationFeedback(feedback,'pt').busy,false);
  feedback.phase='unconfirmed';feedback.status_error='monitoring_timeout';card.hass={language:'en',states};
  assert.match(card.shadowRoot.textContent,/No completion was confirmed within ten minutes/);
  assert.doesNotMatch(card.shadowRoot.textContent,/Completed/);
});

test('mesh feedback explains preparation and measurement without claiming early completion',()=>{
  const operation={action:'test_mesh',phase:'accepted',stage:'preparing_server'};
  assert.match(operationFeedback(operation,'en').note,/Preparing the measurement server/);
  assert.match(operationFeedback(operation,'pt').note,/A preparar o servidor/);
  operation.stage='measuring';operation.phase='running';
  assert.match(operationFeedback(operation,'en').note,/Testing the selected point/);
  operation.phase='failed';
  assert.match(operationFeedback(operation,'en').note,/failed the operation/);
  operation.phase='completed';
  assert.equal(operationFeedback(operation,'en').busy,false);
});
