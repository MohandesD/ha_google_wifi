import './google-wifi-dashboard-ui.js?v=0.12.2';
import './google-wifi-insights-map.js?v=0.12.2';
import './gwi-management.js?v=0.12.2';
import './gwi-locations.js?v=0.12.2';
import {languageOf,overviewPath,mapModel} from './gwi-map-model.js?v=0.12.2';

class GoogleWifiInsightsPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'});
    this._view='overview';
    this._language='en';
  }
  set hass(value) {
    this._hass=value;
    if (!this._timer) this._timer=setTimeout(()=>{this._timer=undefined;this._update();},200);
  }
  set panel(value) { this._panel=value; this._update(); }
  set route(value) { this._select(/(?:^|\/)locations(?:\/|$)/.test(value?.path||'')?'locations':/(?:^|\/)management(?:\/|$)/.test(value?.path||'')?'management':/(?:^|\/)mapa(?:\/|$)/.test(value?.path||'')?'map':'overview'); }
  connectedCallback() { this._update(); }
  disconnectedCallback() { clearTimeout(this._timer);this._timer=undefined; }
  _select(view) { this._view=view;this._update(); }
  _update() {
    const language=languageOf(this._hass);
    const mapPath=this._panel?.config?.map_path||'/google-wifi-insights/mapa';
    const returnPath=overviewPath(this._panel?.config,mapPath);
    if (!this._built) {
      const style=document.createElement('style');
      style.textContent=':host{display:block;background:var(--primary-background-color);min-height:100%;color:var(--primary-text-color)}nav{display:flex;gap:8px;flex-wrap:wrap;position:sticky;top:0;z-index:2;padding:10px 16px;background:var(--card-background-color);border-bottom:1px solid var(--divider-color)}button{font:inherit;min-height:44px;padding:8px 16px;border:0;border-radius:12px;background:transparent;color:var(--primary-text-color);cursor:pointer}button[aria-selected=true]{background:var(--primary-color);color:var(--text-primary-color)}button:focus-visible,select:focus-visible{outline:3px solid var(--primary-color);outline-offset:3px}main{max-width:1600px;margin:auto}main>google-wifi-insights-map{padding:16px}.filters{display:flex;flex-wrap:wrap;gap:14px;padding:14px 20px 0;max-width:1560px;margin:auto}.filters label{display:grid;gap:4px;font:13px system-ui}.filters select{font:14px system-ui;min-height:44px;max-width:min(100%,480px);padding:8px 12px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:inherit}[hidden]{display:none!important}';
      this._nav=document.createElement('nav');this._nav.setAttribute('role','tablist');
      style.textContent+=`:host{container-type:inline-size;--gwi-sticky-offset:65px}*{box-sizing:border-box}
        nav{flex-wrap:nowrap;overflow-x:auto;max-width:100%;scrollbar-width:thin}nav button{flex:none;white-space:nowrap}
        .filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));align-items:end}
        .filters label{min-width:0;max-width:100%}.filters select{width:100%;min-width:0;max-width:100%}
        @container(max-width:460px){nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px;padding:8px}nav button{min-width:0;padding:8px;white-space:normal}.filters{padding:12px 12px 0;gap:10px}}
      `;
      this._buttons={};this._cards={};this._main=document.createElement('main');
      for (const [view,tag] of [['overview','google-wifi-dashboard-ui'],['map','google-wifi-insights-map'],['management','google-wifi-management'],['locations','google-wifi-locations']]) {
        const button=document.createElement('button');button.type='button';button.setAttribute('role','tab');
        button.addEventListener('click',()=>this._select(view));this._buttons[view]=button;this._nav.append(button);
        const card=document.createElement(tag);card.setConfig(view==='map'?{max_clients:8,overview_path:returnPath}:{language:'auto',map_path:mapPath});
        this._cards[view]=card;
      }
      this._filters=document.createElement('div');this._filters.className='filters';this._filterLabels={};this._selectors={};
      for(const key of ['location','network']){
        const label=document.createElement('label'),text=document.createElement('span'),select=document.createElement('select');
        select.addEventListener('change',()=>{this['_'+key]=select.value;if(key==='location')this._network='';this._update();});
        label.append(text,select);this._filterLabels[key]=text;this._selectors[key]=select;this._filters.append(label);
      }
      this.shadowRoot.append(style,this._nav,this._filters,this._main);
      this.shadowRoot.addEventListener('click',event=>{
        const link=event.composedPath().find(node=>node?.tagName==='A'&&[this._mapPath,this._returnPath,this._locationsPath].includes(node.getAttribute('href')));
        if(link){event.preventDefault();this._select(link.getAttribute('href')===this._mapPath?'map':link.getAttribute('href')===this._locationsPath?'locations':'overview');}
      });
      this._built=true;
    }
    this._returnPath=returnPath;this._mapPath=mapPath;this._locationsPath=mapPath.replace(/\/mapa$/,'/locations');
    const networks=mapModel(this._hass?.states),locations=new Map();
    for(const n of networks)if(n.locationId)locations.set(n.locationId,n.locationName);
    if(this._location&&this._location!=='unassigned'&&!locations.has(this._location))this._location='';
    const singleNetwork=this._view==='management';
    const candidates=networks.filter(n=>(!this._location||(n.locationId||'unassigned')===this._location)&&(!singleNetwork||n.source==='google_cloud'));
    if(!candidates.some(n=>n.scope===this._network))this._network='';
    if(singleNetwork&&!this._network)this._network=candidates[0]?.scope||'';
    const filterSignature=JSON.stringify([language,networks.map(n=>[n.scope,n.name,n.source,n.locationId,n.locationName])]);
    if(filterSignature!==this._filterSignature){
      this._filterSignature=filterSignature;
      const option=(value,text)=>{const o=document.createElement('option');o.value=value;o.textContent=text;return o;};
      this._selectors.location.replaceChildren(option('',language==='pt'?'Todas as localizações':'All locations'),option('unassigned',language==='pt'?'Sem localização atribuída':'No location assigned'),...[...locations].sort((a,b)=>a[1].localeCompare(b[1])).map(([id,name])=>option(id,name)));
    }
    const candidateSignature=JSON.stringify([language,singleNetwork,candidates.map(n=>[n.scope,n.name,n.source,n.locationName])]);
    if(candidateSignature!==this._candidateSignature){
      this._candidateSignature=candidateSignature;
      const option=(value,text)=>{const o=document.createElement('option');o.value=value;o.textContent=text;return o;};
      this._selectors.network.replaceChildren(...(!singleNetwork?[option('',language==='pt'?'Todas as redes':'All networks')]:[]),...candidates.map(n=>option(n.scope,[n.locationName,n.name,n.source==='local_status'?(language==='pt'?'Estado local':'Local status'):(language==='pt'?'Conta Google':'Google account')].filter(Boolean).join(' · '))));
    }
    this._selectors.location.value=this._location||'';this._selectors.network.value=this._network||'';
    for(const key of ['location','network']){const text=key==='location'?(language==='pt'?'Casa / edifício / localização':'Home / building / location'):(language==='pt'?'Rede':'Network');this._filterLabels[key].textContent=text;this._selectors[key].setAttribute('aria-label',text);}
    this._filters.hidden=this._view==='locations';
    const config={language:'auto',map_path:mapPath,locations_path:this._locationsPath,overview_path:returnPath,max_clients:8,hide_network_selector:true,location_id:this._location||undefined,network_entity:candidates.find(n=>n.scope===this._network)?.entityId};
    if(JSON.stringify(config)!==this._cardConfig){this._cardConfig=JSON.stringify(config);for(const view of ['overview','map','management'])this._cards[view].setConfig(config);}
    this._language=language;this.lang=language;
    this._nav.setAttribute('aria-label',language==='pt'?'Google WiFi · vistas':'Google WiFi · views');
    for (const [view,button] of Object.entries(this._buttons)) {
      button.textContent={map:language==='pt'?'Mapa':'Map',overview:language==='pt'?'Visão geral':'Overview',management:language==='pt'?'Gestão':'Management',locations:language==='pt'?'Localizações':'Locations'}[view];
      button.setAttribute('aria-selected',String(view===this._view));
      button.setAttribute('tabindex',view===this._view?'0':'-1');
      button.onkeydown=event=>{
        if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
        event.preventDefault();const views=Object.keys(this._buttons),next=event.key==='Home'?views[0]:event.key==='End'?views.at(-1):views[(views.indexOf(view)+(event.key==='ArrowRight'?1:views.length-1))%views.length];
        this._select(next);this._buttons[next].focus();
      };
    }
    const card=this._cards[this._view];
    if(this._main.firstChild!==card)this._main.replaceChildren(card);
    if(this._hass)card.hass=this._hass;
  }
}
if(!customElements.get('google-wifi-insights-panel'))customElements.define('google-wifi-insights-panel',GoogleWifiInsightsPanel);
