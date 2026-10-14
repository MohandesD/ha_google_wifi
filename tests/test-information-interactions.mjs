import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {JSDOM} from 'jsdom';
import * as information from '../www/gwi-information.js';
import * as model from '../www/gwi-map-model.js';

function environment(){
 const dom=new JSDOM('<main></main>',{url:'http://ha.example/google-wifi-insights/overview',pretendToBeVisual:true});
 const host=dom.window.document.querySelector('main');
 return {dom,host};
}
const network=(at='first')=>({networkInfo:{retrieved_at:at,cloud:{lan_settings:{ipAddress:'10.7.0.1'}},extra:Array.from({length:100},(_,i)=>({i,reading:at}))}});

test('disclosures have visible actions, a chevron, keyboard focus and native open/close behaviour',()=>{
 const {host}=environment();
 information.renderInformation(host,information.networkInformation(network()),'home');
 const details=host.querySelector('details'),summary=details.querySelector('summary'),pre=details.querySelector('pre');
 assert.match(summary.textContent,/All supplied information/);
 assert.match(summary.textContent,/Expand/);assert.match(summary.textContent,/Collapse/);
 assert.ok(summary.querySelector('svg[aria-hidden="true"]'));
 assert.equal(pre.tabIndex,0);assert.equal(pre.getAttribute('role'),'region');
 summary.click();assert.equal(details.open,true);
 summary.click();assert.equal(details.open,false);
 const pt=information.pointInformation({firmwareInfo:{}},'pt');
 assert.match(pt,/Expandir/);assert.match(pt,/Recolher/);
 assert.doesNotMatch(information.informationSummary('<img src=x onerror=bad>'),/<img/);
});

test('new telemetry updates JSON in place while retaining expansion, focus and both scroll offsets',()=>{
 const {host,dom}=environment();
 information.renderInformation(host,information.networkInformation(network()),'home');
 const details=host.querySelector('details'),summary=details.querySelector('summary'),pre=details.querySelector('pre');
 summary.click();pre.focus();pre.scrollTop=320;pre.scrollLeft=19;
 information.renderInformation(host,information.networkInformation(network('second')),'home');
 assert.equal(host.querySelector('details'),details);assert.equal(host.querySelector('pre'),pre);
 assert.equal(details.open,true);assert.equal(dom.window.document.activeElement,pre);
 assert.equal(pre.scrollTop,320);assert.equal(pre.scrollLeft,19);
 assert.match(pre.textContent,/second/);assert.doesNotMatch(pre.textContent,/first/);
});

test('closing a disclosure remains closed after subsequent updates, including an unchanged update',()=>{
 const {host}=environment();
 const first=information.networkInformation(network());
 information.renderInformation(host,first,'home');
 const details=host.querySelector('details'),summary=details.querySelector('summary');
 summary.click();summary.click();summary.focus();
 information.renderInformation(host,first,'home');
 information.renderInformation(host,information.networkInformation(network('new')),'home');
 assert.equal(host.querySelector('summary'),summary);assert.equal(details.open,false);
 assert.equal(host.ownerDocument.activeElement,summary);
});

test('keyed point disclosures retain the correct state when a point is inserted or removed',()=>{
 const {host}=environment();
 const point=(id)=>`<details data-gwi-disclosure="${id}">${information.informationSummary(id)}<pre data-gwi-scroll="${id}">${id}</pre></details>`;
 information.renderInformation(host,point('a')+point('b'),'home');
 const b=host.querySelector('[data-gwi-disclosure="b"]');b.querySelector('summary').click();
 information.renderInformation(host,point('new')+point('b'),'home');
 assert.equal(host.querySelector('[data-gwi-disclosure="b"]'),b);assert.equal(b.open,true);
 assert.equal(host.querySelector('[data-gwi-disclosure="a"]'),null);
});

test('switching networks does not inherit another network disclosure state',()=>{
 const {host}=environment();
 const markup=information.networkInformation(network());
 information.renderInformation(host,markup,'first');host.querySelector('summary').click();
 information.renderInformation(host,markup,'second');assert.equal(host.querySelector('details').open,false);
});

const states={
 'sensor.network_info':{state:'available',attributes:{gwi_scope:'home',gwi_kind:'network',gwi_metric:'network_information_status',network_information:network().networkInfo}},
 'sensor.point':{state:'1',attributes:{gwi_scope:'home',gwi_kind:'point',gwi_metric:'clients',gwi_item_id:'point',device_name:'Test point'}},
 'sensor.firmware':{state:'idle',attributes:{gwi_scope:'home',gwi_kind:'point',gwi_metric:'update_status',gwi_item_id:'point',firmware_information:{installed_version:'test',release_notes:{notes:[]}}}},
};
async function cardEnvironment(file,type){
 const {dom}=environment(),{window}=dom;
 class History extends window.HTMLElement{configure(){}}
 window.customElements.define('gwi-usage-history',History);
 const context=vm.createContext({...information,...model,formatBytes:value=>value==null?'—':String(value)+' B',window,document:window.document,HTMLElement:window.HTMLElement,
  customElements:window.customElements,CustomEvent:window.CustomEvent,ResizeObserver:class{observe(){}disconnect(){}},
  requestAnimationFrame:()=>1,cancelAnimationFrame(){},setTimeout,clearTimeout,setInterval:()=>1,clearInterval(){}});
 const source=await readFile(new URL('../www/'+file,import.meta.url),'utf8');
 vm.runInContext(source.replace(/^import[^\n]*\n/gm,'').replace(/^export /gm,''),context);
 const card=window.document.createElement(type);window.document.body.append(card);
 card.setConfig({});card.hass={states,language:'en',config:{time_zone:'UTC'}};card._update?.();
 return {card,dom};
}

test('overview state updates retain the information panel outside the refreshed traffic region',async()=>{
 const {card}=await cardEnvironment('google-wifi-dashboard-ui.js','google-wifi-dashboard-ui');
 const panel=card.shadowRoot.querySelector('[data-gwi-information-panels]');
 const details=panel.querySelector('details'),pre=details.querySelector('pre');
 details.querySelector('summary').click();pre.scrollTop=210;pre.focus();
 const next=structuredClone(states);next['sensor.network_info'].attributes.network_information=network('new').networkInfo;
 card.hass={states:next,language:'en',config:{time_zone:'UTC'}};card._update();
 assert.equal(card.shadowRoot.querySelector('[data-gwi-information-panels]'),panel);
 assert.equal(panel.querySelector('details'),details);assert.equal(pre.scrollTop,210);
 assert.equal(card.shadowRoot.activeElement,pre);assert.match(pre.textContent,/new/);
 details.querySelector('summary').click();card.hass={states:next,language:'en'};card._update();
 assert.equal(details.open,false);card.remove();
});

test('map updates retain both outer and nested firmware disclosures and JSON position',async()=>{
 const {card}=await cardEnvironment('google-wifi-insights-map.js','google-wifi-insights-map');
 const outer=card.shadowRoot.querySelector('[data-gwi-disclosure="home:point"]');
 outer.querySelector('summary').click();
 const raw=outer.querySelector('[data-gwi-disclosure="point-all"]'),pre=raw.querySelector('pre');
 raw.querySelector('summary').click();pre.scrollTop=190;pre.focus();
 const next=structuredClone(states);next['sensor.firmware'].attributes.firmware_information.installed_version='updated';
 card.hass={states:next,language:'en'};
 assert.equal(card.shadowRoot.querySelector('[data-gwi-disclosure="home:point"]'),outer);
 assert.equal(outer.open,true);assert.equal(raw.open,true);assert.equal(pre.scrollTop,190);
 assert.equal(card.shadowRoot.activeElement,pre);assert.match(pre.textContent,/updated/);
 outer.querySelector('summary').click();card.hass={states,language:'en'};
 assert.equal(outer.open,false);card.remove();
});
