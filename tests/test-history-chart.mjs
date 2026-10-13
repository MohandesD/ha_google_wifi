import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import {mapModel} from '../www/gwi-map-model.js';
const source=await readFile(new URL('../www/gwi-usage-history.js',import.meta.url),'utf8');
function setup(){
 class Node{children=[];attributes={};listeners={};constructor(tag){this.tag=tag;}attachShadow(){return this.shadowRoot=new Node('shadow');}replaceChildren(...v){this.children=[...v];}append(...v){this.children.push(...v);}setAttribute(k,v){this.attributes[k]=v;}addEventListener(k,v){this.listeners[k]=v;}get textContent(){return(this.text||'')+this.children.map(c=>c.textContent).join(' ');}set textContent(v){this.text=String(v);}}
 const classes=new Map();const context=vm.createContext({HTMLElement:Node,document:{createElement:tag=>new Node(tag),createElementNS:(ns,tag)=>Object.assign(new Node(tag),{namespaceURI:ns})},customElements:{get:key=>classes.get(key),define:(key,value)=>classes.set(key,value)}});
 vm.runInContext(source.replace(/export /g,''),context);
 return {chart:new(classes.get('gwi-usage-history'))(),format:vm.runInContext('formatBytes',context)};
}
test('byte formatting preserves missing values and uses decimal units',()=>{const {format}=setup();for(const value of [null,undefined,true,-1,'NaN'])assert.equal(format(value),'—');assert.equal(format(0),'0 B');assert.equal(format(1500000000),'1.5 GB');});
test('chart obtains requested resolution from HA response and shows missing buckets',async()=>{
 const {chart}=setup();const calls=[];chart.configure({entityId:'sensor.client',language:'en',series:[],api:{callWS:async command=>{calls.push(command);return {response:{period:{start:'2026-10-13T11:00:00Z',end:'2026-10-13T12:00:00Z',granularity_seconds:60},series:[{start:'2026-10-13T11:00:00Z',end:'2026-10-13T11:01:00Z',download_bytes:1000,upload_bytes:0}]}};}}});
 await chart._load('minute');assert.equal(calls.at(-1).service_data.resolution,'minute');assert.equal(calls.at(-1).service_data.entity_id,'sensor.client');assert.equal(calls.at(-1).return_response,true);assert.match(chart.shadowRoot.textContent,/1 \/ 60/);assert.match(chart.shadowRoot.textContent,/Missing buckets/);assert.match(chart.shadowRoot.textContent,/1 kB/);
});
test('frontend test and action bindings stay within the selected network',()=>{
 const attrs={gwi_scope:'one',gwi_kind:'client',gwi_item_id:'client',gwi_metric:'point',connected:true,device_name:'Google (HA)',wifi_test_mbps:42,wifi_test_at:'2025-01-01T00:00:00Z',wifi_test_point:'Old point'};
 const model=mapModel({'sensor.client':{state:'Point',attributes:attrs},'button.client':{state:'unknown',attributes:{...attrs,gwi_metric:'prioritize_client'}},'button.foreign':{state:'unknown',attributes:{...attrs,gwi_scope:'two',gwi_metric:'prioritize_client'}}},{network_entity:'sensor.client'})[0];
 assert.equal(model.clients[0].wifiTest,42);assert.equal(model.clients[0].wifiTestPoint,'Old point');assert.equal(model.clients[0].controls.length,1);assert.equal(model.clients[0].controls[0].entityId,'button.client');assert.equal(model.clients[0].signal.rssi,undefined);
});
