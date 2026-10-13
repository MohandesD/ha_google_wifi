import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {languageOf,overviewPath} from '../www/gwi-map-model.js';

const source=await readFile(new URL('../custom_components/google_wifi_insights/frontend/google-wifi-insights-panel.js',import.meta.url),'utf8');
function environment() {
  const jobs=[];const elements=new Map();
  class Node {
    constructor(tag='host'){this.tagName=tag.toUpperCase();this.children=[];this.attributes={};this.listeners={};}
    append(...children){this.children.push(...children);}
    replaceChildren(...children){this.children=children;}
    get firstChild(){return this.children[0];}
    attachShadow(){return this.shadowRoot=new Node('shadow');}
    setAttribute(name,value){this.attributes[name]=value;}
    addEventListener(type,listener){this.listeners[type]=listener;}
    focus(){this.focused=true;}
  }
  class Card extends Node {
    setConfig(value){this.config=value;}
    set hass(value){this.lastHass=value;this.updates=(this.updates||0)+1;}
  }
  const context=vm.createContext({HTMLElement:Node,languageOf,overviewPath,
    document:{createElement:tag=>tag.startsWith('google-wifi')?new Card(tag):new Node(tag)},
    customElements:{get:key=>elements.get(key),define:(key,value)=>elements.set(key,value)},
    setTimeout:callback=>{jobs.push(callback);return jobs.length;},clearTimeout(){},
  });
  vm.runInContext(source.replace(/^import[^\n]*\n/gm,''),context);
  const panel=new (elements.get('google-wifi-insights-panel'))();panel.connectedCallback();
  return {panel,jobs};
}

test('bundled panel keeps existing view instances and respects alternate HA routes',()=>{
  const {panel}=environment();
  panel.panel={config:{map_path:'/alternate-panel/mapa'}};
  const overview=panel._cards.overview;
  assert.equal(overview.config.map_path,'/alternate-panel/mapa');
  panel.route={path:'/mapa'};
  assert.equal(panel._main.firstChild,panel._cards.map);
  panel.route={path:'/overview'};
  assert.equal(panel._main.firstChild,overview);
});

test('panel coalesces HA updates and follows the HA user language',()=>{
  const {panel,jobs}=environment();
  for(let i=0;i<30;i++)panel.hass={language:'pt-PT',states:{counter:i}};
  assert.equal(jobs.length,1);jobs[0]();
  assert.equal(panel._cards.overview.lastHass.states.counter,29);
  assert.equal(panel._cards.overview.updates,1);
  assert.equal(panel._cards.map.updates,undefined);
  assert.equal(panel._buttons.map.textContent,'Mapa');
  assert.equal(panel._buttons.overview.textContent,'Visão geral');
});

test('panel tabs support keyboard selection and more-info events can bubble',()=>{
  const {panel}=environment();
  let prevented=false;
  panel._buttons.overview.onkeydown({key:'ArrowRight',preventDefault(){prevented=true;}});
  assert.equal(prevented,true);
  assert.equal(panel._buttons.map.attributes['aria-selected'],'true');
  assert.equal(panel._buttons.map.focused,true);
  panel._buttons.map.onkeydown({key:'Home',preventDefault(){}});
  assert.equal(panel._buttons.overview.attributes['aria-selected'],'true');
  assert.equal(panel.shadowRoot.listeners['hass-more-info'],undefined);
});

test('map and return links keep navigation inside the bundled panel',()=>{
  const {panel}=environment();
  panel.panel={config:{map_path:'/alternate-panel/mapa'}};
  const overview=panel._cards.overview;
  assert.equal(panel._cards.map.config.overview_path,'/alternate-panel/overview');
  function click(href) {
    let prevented=false;
    const link={tagName:'A',getAttribute:()=>href};
    panel.shadowRoot.listeners.click({composedPath:()=>[link],preventDefault(){prevented=true;}});
    return prevented;
  }
  assert.equal(click('/alternate-panel/mapa'),true);
  assert.equal(panel._main.firstChild,panel._cards.map);
  assert.equal(click('/alternate-panel/overview'),true);
  assert.equal(panel._main.firstChild,overview);
  assert.equal(click('/config/integrations'),false);
});
