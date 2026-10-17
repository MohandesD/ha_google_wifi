import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
import {mapModel} from '../www/gwi-map-model.js';
const source=await readFile(new URL('../www/gwi-usage-history.js',import.meta.url),'utf8');
function setup(){
 const dom=new JSDOM('<main></main>',{pretendToBeVisual:true});
 const context=vm.createContext({HTMLElement:dom.window.HTMLElement,document:dom.window.document,customElements:dom.window.customElements});
 vm.runInContext(source.replace(/export /g,''),context);
 const chart=dom.window.document.createElement('gwi-usage-history');dom.window.document.querySelector('main').append(chart);
 return {dom,chart,root:chart.shadowRoot,format:vm.runInContext('formatBytes',context),rows:vm.runInContext('usageRows',context)};
}
const series=Array.from({length:24},(_,i)=>({start:new Date(Date.UTC(2026,9,13,i)).toISOString(),end:new Date(Date.UTC(2026,9,13,i+1)).toISOString(),download_bytes:i*1234567,upload_bytes:i*10000}));
const config=(extra={})=>({entityId:'sensor.example',language:'en',timeZone:'Europe/Lisbon',series,summary:{start:series[0].start,end:series.at(-1).end,granularity_seconds:3600},...extra});
const press=(root,text)=>{const b=[...root.querySelectorAll('button')].find(b=>b.textContent===text);assert.ok(b,text);b.click();};
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

test('axes show bytes and HA-local times; clicking a bucket reveals exact values and local zoom',()=>{
 const {chart,root,dom}=setup();chart.configure(config());
 assert.match(root.querySelector('.y-tick').textContent,/0 B/);assert.match(root.querySelectorAll('.x-tick')[0].textContent,/01:00|1:00/);
 assert.match(root.querySelector('svg').textContent,/Europe\/Lisbon/);
 const bars=root.querySelectorAll('.bucket');assert.equal(bars.length,24);bars[10].dispatchEvent(new dom.window.MouseEvent('click'));
 assert.match(root.querySelector('.detail').textContent,/12,345,670 B/);assert.equal(root.querySelectorAll('[aria-pressed="true"].bucket').length,1);
 press(root,'Zoom around this interval');assert.equal(root.querySelectorAll('.bucket').length,5);assert.match(root.textContent,/no finer measurements are inferred/);
 press(root,'Show full period');assert.equal(root.querySelectorAll('.bucket').length,24);
 root.querySelector('.bucket[aria-pressed=true]').dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));
 assert.equal(root.querySelector('.bucket[aria-pressed=true]').getAttribute('data-start'),series[11].start);
 assert.equal(root.activeElement,root.querySelector('.bucket[aria-pressed=true]'));
});

test('selection, zoom, horizontal scroll and record disclosure survive refreshed chart instances',async()=>{
 const {chart,root,dom}=setup();chart.configure(config());
 root.querySelectorAll('.bucket')[10].dispatchEvent(new dom.window.MouseEvent('click'));press(root,'Zoom around this interval');
 const scroller=root.querySelector('.plot-scroll');scroller.scrollLeft=88;scroller.dispatchEvent(new dom.window.Event('scroll'));
 root.querySelector('summary').click();await new Promise(resolve=>setTimeout(resolve,10));
 const replacement=dom.window.document.createElement('gwi-usage-history');chart.replaceWith(replacement);replacement.configure(config());
 const next=replacement.shadowRoot;assert.equal(next.querySelectorAll('.bucket').length,5);assert.match(next.querySelector('.detail').textContent,/12,345,670 B/);
 assert.equal(next.querySelector('.plot-scroll').scrollLeft,88);assert.equal(next.querySelector('details').open,true);
 replacement.configure(config({entityId:'sensor.another_home'}));assert.equal(next.querySelector('.detail'),null);assert.equal(next.querySelector('details').open,false);assert.equal(next.querySelectorAll('.bucket').length,24);
});

test('unknown directional data is distinct from zero and missing intervals remain spatial gaps',()=>{
 const {chart,root,dom,rows}=setup();const sparse=[{...series[0],download_bytes:null,upload_bytes:0},{...series[3],download_bytes:100,upload_bytes:undefined},{...series[1],end:'invalid'}];
 chart.configure(config({series:sparse}));assert.equal(rows(sparse).length,2);
 const bars=root.querySelectorAll('.bucket');assert.equal(bars.length,2);
 assert.ok(Number(bars[1].querySelector('.selection').getAttribute('x'))-Number(bars[0].querySelector('.selection').getAttribute('x'))>80);
 bars[0].dispatchEvent(new dom.window.MouseEvent('click'));assert.match(root.querySelector('.detail').textContent,/Not supplied/);assert.match(root.querySelector('.detail').textContent,/0 B/);assert.match(root.textContent,/2 \/ 24/);
 assert.match(root.textContent,/Missing buckets/);assert.equal(root.querySelectorAll('tbody tr').length,2);
});

test('stale history responses cannot overwrite a newer resolution or another entity',async()=>{
 const {chart,root}=setup(),pending=[];const api={callWS:request=>new Promise(resolve=>pending.push({request,resolve}))};chart.configure(config({api}));
 const minute=chart._load('minute'),day=chart._load('day');assert.equal(pending.length,2);
 pending[1].resolve({response:{series:[series[2]],period:{}}});await day;
 pending[0].resolve({response:{series:[series[7]],period:{}}});await minute;assert.equal(chart._mode,'day');assert.equal(root.querySelector('.bucket').getAttribute('data-start'),series[2].start);
 const old=chart._load('minute');chart.configure(config({entityId:'sensor.other'}));pending[2].resolve({response:{series:[series[7]],period:{}}});await old;
 assert.equal(chart._mode,'hour');assert.equal(root.querySelectorAll('.bucket').length,24);
});

test('cached summaries retain the requested period and gaps for an all-zero sample',()=>{
 const {chart,root,dom}=setup(),zero={...series[3],download_bytes:0,upload_bytes:0};
 chart.configure(config({series:[zero],summary:{period:{start:series[0].start,end:series.at(-1).end,granularity_seconds:3600}}}));
 assert.match(root.textContent,/1 \/ 24/);assert.equal(root.querySelectorAll('.y-tick').length,2);
 assert.ok(Number(root.querySelector('.selection').getAttribute('x'))>78);
 root.querySelector('.bucket').dispatchEvent(new dom.window.MouseEvent('click'));assert.equal(root.querySelectorAll('.detail .value').length,3);
 for(const value of root.querySelectorAll('.detail .value'))assert.equal(value.textContent,'0 B');
});

test('a refreshed non-hour chart keeps its selected records visible while HA responds',async()=>{
 const {chart,root,dom}=setup();let reply;
 const api={callWS:()=>new Promise(resolve=>reply=resolve)};chart.configure(config({api}));const load=chart._load('day');reply({response:{series:series.slice(0,7),period:{}}});await load;
 root.querySelectorAll('.bucket')[3].dispatchEvent(new dom.window.MouseEvent('click'));
 const replacement=dom.window.document.createElement('gwi-usage-history');chart.replaceWith(replacement);replacement.configure(config({api}));
 assert.equal(replacement._loading,true);assert.equal(replacement.shadowRoot.querySelectorAll('.bucket').length,7);assert.match(replacement.shadowRoot.querySelector('.detail').textContent,/3,703,701 B/);
 const rootBefore=replacement.shadowRoot.querySelector('.plot-scroll');rootBefore.scrollLeft=20;
 reply({response:{series:series.slice(0,7),period:{}}});await new Promise(resolve=>setImmediate(resolve));assert.equal(replacement._loading,false);assert.equal(replacement.shadowRoot.querySelector('.plot-scroll').scrollLeft,20);
 assert.equal(replacement.shadowRoot.querySelector('.bucket[aria-pressed=true]').getAttribute('data-start'),series[3].start);
});
