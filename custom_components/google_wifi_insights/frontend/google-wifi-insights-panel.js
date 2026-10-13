import './google-wifi-dashboard-ui.js?v=0.8.2';
import './google-wifi-insights-map.js?v=0.8.2';
import {languageOf,overviewPath} from './gwi-map-model.js?v=0.8.2';

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
  set route(value) { this._select(/(?:^|\/)mapa(?:\/|$)/.test(value?.path||'')?'map':'overview'); }
  connectedCallback() { this._update(); }
  disconnectedCallback() { clearTimeout(this._timer);this._timer=undefined; }
  _select(view) { this._view=view;this._update(); }
  _update() {
    const language=languageOf(this._hass);
    const mapPath=this._panel?.config?.map_path||'/google-wifi-insights/mapa';
    const returnPath=overviewPath(this._panel?.config,mapPath);
    if (!this._built) {
      const style=document.createElement('style');
      style.textContent=':host{display:block;background:var(--primary-background-color);min-height:100%;color:var(--primary-text-color)}nav{display:flex;gap:8px;position:sticky;top:0;z-index:2;padding:10px 16px;background:var(--card-background-color);border-bottom:1px solid var(--divider-color)}button{font:inherit;min-height:44px;padding:8px 16px;border:0;border-radius:12px;background:transparent;color:var(--primary-text-color);cursor:pointer}button[aria-selected=true]{background:var(--primary-color);color:var(--text-primary-color)}button:focus-visible{outline:3px solid var(--primary-color);outline-offset:3px}main{max-width:1600px;margin:auto}main>google-wifi-insights-map{padding:16px}';
      this._nav=document.createElement('nav');this._nav.setAttribute('role','tablist');
      this._buttons={};this._cards={};this._main=document.createElement('main');
      for (const [view,tag] of [['overview','google-wifi-dashboard-ui'],['map','google-wifi-insights-map']]) {
        const button=document.createElement('button');button.type='button';button.setAttribute('role','tab');
        button.addEventListener('click',()=>this._select(view));this._buttons[view]=button;this._nav.append(button);
        const card=document.createElement(tag);card.setConfig(view==='map'?{max_clients:8,overview_path:returnPath}:{language:'auto',map_path:mapPath});
        this._cards[view]=card;
      }
      this.shadowRoot.append(style,this._nav,this._main);
      this.shadowRoot.addEventListener('click',event=>{
        const link=event.composedPath().find(node=>node?.tagName==='A'&&[this._mapPath,this._returnPath].includes(node.getAttribute('href')));
        if(link){event.preventDefault();this._select(link.getAttribute('href')===this._mapPath?'map':'overview');}
      });
      this._built=true;
    }
    if (mapPath!==this._mapPath || returnPath!==this._returnPath) {
      this._returnPath=returnPath;this._cards.map.setConfig({max_clients:8,overview_path:returnPath});
      this._mapPath=mapPath;this._cards.overview.setConfig({language:'auto',map_path:mapPath});
    }
    this._language=language;this.lang=language;
    this._nav.setAttribute('aria-label',language==='pt'?'Google WiFi · vistas':'Google WiFi · views');
    for (const [view,button] of Object.entries(this._buttons)) {
      button.textContent=view==='map'?(language==='pt'?'Mapa':'Map'):(language==='pt'?'Visão geral':'Overview');
      button.setAttribute('aria-selected',String(view===this._view));
      button.setAttribute('tabindex',view===this._view?'0':'-1');
      button.onkeydown=event=>{
        if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
        event.preventDefault();const next=event.key==='Home'?'overview':event.key==='End'?'map':view==='map'?'overview':'map';
        this._select(next);this._buttons[next].focus();
      };
    }
    const card=this._cards[this._view];
    if(this._main.firstChild!==card)this._main.replaceChildren(card);
    if(this._hass)card.hass=this._hass;
  }
}
if(!customElements.get('google-wifi-insights-panel'))customElements.define('google-wifi-insights-panel',GoogleWifiInsightsPanel);
