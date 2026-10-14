import { mapModel, translate, languageOf, isLocalHaPath, overviewPath, operationFeedback } from "./gwi-map-model.js?v=0.9.2";
import {formatBytes} from "./gwi-usage-history.js?v=0.9.2";
import {pointInformation,networkInformation,informationSummary,informationCss,renderInformation} from "./gwi-information.js?v=0.9.2";

const CSS = `
  :host { display:block; color:var(--primary-text-color); font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif); }
  * { box-sizing:border-box; }
  ha-card { display:block; background:var(--ha-card-background,var(--card-background-color)); border-radius:var(--ha-card-border-radius,12px); }
  .content { padding:20px; container-type:inline-size; }
  .back-link { display:inline-flex; align-items:center; gap:8px; min-height:44px; margin:0 0 12px; padding:8px 12px; border:1px solid var(--divider-color); border-radius:8px; color:var(--primary-text-color); font-size:14px; text-decoration:none; }
  .back-link:hover { background:var(--secondary-background-color); }
  .back-link:focus-visible { outline:2px solid var(--primary-color); outline-offset:3px; }
  h2 { font-size:20px; font-weight:500; margin:0 0 8px; }
  h3 { font-size:14px; font-weight:500; margin:18px 0 4px; }
  p { font-size:12px; line-height:1.5; margin:6px 0; color:var(--secondary-text-color); }
  .legend { display:flex; flex-wrap:wrap; gap:8px 16px; margin:12px 0 20px; font-size:12px; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .dot { width:8px; height:8px; border-radius:50%; background:var(--secondary-text-color); display:inline-block; }
  .good { --signal-color:var(--success-color,#43a047); }
  .excellent { --signal-color:var(--success-color,#43a047); }
  .fair { --signal-color:var(--warning-color,#ffa600); }
  .weak { --signal-color:var(--error-color,#db4437); }
  .unknown { --signal-color:var(--secondary-text-color); }
  .dot.signal { background:var(--signal-color); }
  .cluster { position:relative; display:grid; grid-template-columns:160px minmax(0,1fr); gap:58px; align-items:center; padding:14px 0 24px; }
  .edges { position:absolute; top:0; left:0; width:100%; height:100%; overflow:visible; pointer-events:none; z-index:0; }
  .edges path { fill:none; stroke:var(--signal-color); stroke-width:1.5; }
  .edges path.unknown { stroke-dasharray:3 4; opacity:.7; }
  button { position:relative; z-index:1; color:inherit; background:var(--ha-card-background,var(--card-background-color)); font:inherit; text-align:left; border:0; padding:8px; border-radius:8px; min-width:0; }
  button:focus-visible { outline:2px solid var(--primary-color); outline-offset:3px; }
  button:hover { background:var(--secondary-background-color); }
  .point { display:flex; flex-direction:column; gap:6px; align-items:center; width:160px; text-align:center; }
  .point .circle { width:54px; height:54px; display:grid; place-items:center; border:1px solid var(--divider-color); border-radius:50%; font-size:14px; font-weight:500; }
  .point.primary .circle { border:2px solid var(--primary-color); }
  .name { display:block; font-size:14px; font-weight:500; overflow-wrap:anywhere; }
  .meta { display:block; font-size:12px; color:var(--secondary-text-color); line-height:1.45; overflow-wrap:anywhere; }
  .status { display:flex; gap:5px; align-items:center; font-size:12px; }
  .status .online { background:var(--success-color); }
  .status .offline { background:var(--error-color); }
  .clients { display:grid; grid-template-columns:minmax(0,1fr); gap:12px; align-content:center; min-width:0; }
  .client,.mesh-point { display:grid; grid-template-columns:25px minmax(0,1fr); gap:8px; min-height:54px; }
  .mesh-overview { border-bottom:1px solid var(--divider-color); margin-bottom:18px; padding-bottom:22px; }
  .mesh-point { border:1px solid var(--divider-color); }
  .mesh-overview .edges path { stroke-dasharray:6 4; }
  .mesh-ratings { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:8px; margin:12px 0; }
  .peer-list { display:grid; gap:8px; padding:8px 0 12px; font-size:12px; color:var(--secondary-text-color); }
  details summary { cursor:pointer; font-size:12px; color:var(--primary-color); padding:8px 0; }
  .client-row { position:relative; z-index:1; background:var(--ha-card-background,var(--card-background-color)); }
  .client-row .client { width:100%; }
  .actions { display:flex; flex-wrap:wrap; gap:4px 16px; padding-left:41px; }
  .actions button,.actions a { color:var(--primary-color); font-size:12px; text-decoration:none; padding:4px 0; }
  .action-control { display:flex; flex-direction:column; align-items:flex-start; gap:4px; padding:4px 0; }
  .action-status { display:inline-flex; align-items:center; gap:6px; padding:5px 8px; font-size:12px; color:var(--primary-text-color); border:1px solid var(--divider-color); border-left:4px solid var(--secondary-text-color); border-radius:6px; }
  .action-status.busy { border-left-color:var(--primary-color); }
  .action-status.completed { border-left-color:var(--success-color); }
  .action-status.failed { border-left-color:var(--error-color); }
  .action-status.unconfirmed { border-left-color:var(--warning-color); }
  .action-banner { padding:12px; margin:12px 0; border:1px solid var(--divider-color); border-radius:8px; }
  .action-banner strong { display:block; margin-bottom:8px; font-size:14px; }
  .action-spinner { display:inline-block; animation:action-spin 1.2s linear infinite; }
  @keyframes action-spin { to { transform:rotate(360deg); } }
  @media (prefers-reduced-motion:reduce) { .action-spinner { animation:none; } }
  .summary { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0 16px; }
  .summary span { padding:5px 9px; border-radius:6px; background:var(--secondary-background-color); font-size:12px; }
  .weak-count { color:var(--error-color,#db4437); }
  .wired-icon { font-size:23px; line-height:30px; color:var(--secondary-text-color); }
  .bars { display:flex; gap:2px; align-items:flex-end; width:25px; height:23px; margin-top:5px; }
  .bar { width:4px; background:var(--divider-color); border-radius:1px; }
  .bar.active { background:var(--signal-color); }
  .bar:nth-child(1) { height:7px; } .bar:nth-child(2) { height:12px; } .bar:nth-child(3) { height:17px; } .bar:nth-child(4) { height:22px; }
  .more { font-size:12px; color:var(--primary-color); }
  .empty { font-size:12px; color:var(--secondary-text-color); padding:12px 0; }
  .unassigned { padding:8px 0 16px; }
  @container (max-width:500px) { .cluster { grid-template-columns:minmax(0,1fr); gap:34px; } .point { justify-self:center; } .clients { padding-left:28px; } }
  @media (pointer:coarse) { button { min-height:44px; } }
`;

function element(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = String(text);
  return e;
}

class GoogleWifiInsightsMap extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:"open"}); this._language="en"; this._contexts=new Map(); this._expanded = new Set(); this._observer = new ResizeObserver(() => this._drawEdges()); }
  setConfig(config) {
    this._config = { max_clients:8, ...config };
    if ((this._config.title!=null && typeof this._config.title !== "string") || !Number.isInteger(this._config.max_clients) || this._config.max_clients < 1 || this._config.max_clients > 100)
      throw new Error(translate(this._language)("config_error"));
    if (this._config.overview_path != null && !isLocalHaPath(this._config.overview_path))
      throw new Error(translate(this._language)("navigation_config_error"));
    this._signature=undefined;
    this._updateStates(this._states || {});
  }
  set hass(value) { this._hass = value; this._setInternationalization(value); this._updateStates(value?.states || {}); }
  _setInternationalization = value => {
    if(!value || (!value.language && !value.locale?.language))return;
    const language=languageOf(value);
    if(language===this._language)return;
    this._language=language; this._updateStates(this._states || {});
  };
  _updateStates = (states, unsubscribe) => {
    if (unsubscribe) this._unsubscribe = unsubscribe;
    this._states = states || {};
    const model = mapModel(this._states, this._config, this._language);
    const signature = JSON.stringify({language:this._language,model});
    if (signature === this._signature && this.shadowRoot.children.length) return;
    this._signature = signature; this._model = model; this._render();
  };
  _queueStates = states => {
    this._states=states || {};
    if(typeof setTimeout!=="function")return this._updateStates(this._states);
    if(this._stateTimer)return;
    this._stateTimer=setTimeout(()=>{this._stateTimer=undefined;this._updateStates(this._states);},200);
  };
  connectedCallback() {
    for(const [context,callback] of [["states",this._queueStates],["hassInternationalization",this._setInternationalization],["locale",this._setInternationalization],["hassApi",value=>{this._api=value;this._signature=undefined;this._queueStates(this._states || {});}]]) {
      const event = new CustomEvent("context-request", {bubbles:true, composed:true, cancelable:true});
      event.context=context; event.subscribe=true;
      event.callback=(value,unsubscribe)=>{if(unsubscribe)this._contexts.set(context,unsubscribe);callback(value);};
      this.dispatchEvent(event);
    }
    this._observer.observe(this); this._render();
  }
  disconnectedCallback() { if(this._stateTimer)clearTimeout(this._stateTimer);this._stateTimer=undefined;this._unsubscribe?.(); this._unsubscribe = undefined; for(const unsubscribe of this._contexts.values())unsubscribe(); this._contexts.clear(); this._observer.disconnect(); cancelAnimationFrame(this._frame); }
  getCardSize() { return Math.max(4, Math.ceil((this.offsetHeight || 400) / 50)); }
  getGridOptions() { return { columns:12, min_columns:6 }; }
  _moreInfo(entityId) { this.dispatchEvent(new CustomEvent("hass-more-info", {detail:{entityId}, bubbles:true, composed:true})); }
  _operationBadge(operation) {
    const feedback=operationFeedback(operation,this._language);
    if(!feedback)return null;
    const badge=element("span","action-status "+feedback.phase+(feedback.busy?" busy":""));badge.setAttribute("role","status");
    const symbol=element("span",feedback.busy?"action-spinner":null,feedback.symbol);symbol.setAttribute("aria-hidden","true");
    badge.append(symbol,document.createTextNode(feedback.label));badge.title=feedback.note;return badge;
  }
  _operationBanner(operation) {
    const feedback=operationFeedback(operation,this._language);
    if(!feedback)return null;
    const banner=element("div","action-banner");banner.setAttribute("role","status");
    banner.append(element("strong",null,feedback.actionLabel+(operation.target_name?" · "+operation.target_name:"")),this._operationBadge(operation));
    if(feedback.at)banner.append(element("p",null,new Date(feedback.at).toLocaleString(this._language,{timeZone:this._hass?.config?.time_zone||undefined})));
    banner.append(element("p",null,feedback.note));return banner;
  }
  _controls(controls) {
    const actions=element("div","actions");
    for(const control of controls || []) {
      const button=element("button",null,control.name);button.type="button";button.disabled=control.state==="unavailable";
      button.addEventListener("click",()=>this._moreInfo(control.entityId));
      const wrapper=element("div","action-control");wrapper.append(button);
      const badge=this._operationBadge(control.feedback);if(badge)wrapper.append(badge);
      actions.append(wrapper);
    }
    return actions;
  }
  _history(item,entityId) {
    const history=element("gwi-usage-history");
    history.configure({entityId,language:this._language,api:this._api || this._hass,series:item.usageHourly || [],summary:item.usageWindows?.hour});
    return history;
  }
  _clientNode(client) {
    const t=translate(this._language);
    const node = element("button", "client " + client.signal.key);
    node.type = "button"; node.dataset.entity = client.entityId;
    node.setAttribute("aria-label", t("client_details",{name:client.name,quality:client.signal.label,point:client.pointName || t("unknown_point")}));
    const bars = element("span", client.signal.wired ? "wired-icon" : "bars",client.signal.wired ? "↔" : undefined); bars.setAttribute("aria-hidden","true");
    if(!client.signal.wired) for(let i=0;i<4;i++) bars.append(element("span","bar" + (i<client.signal.bars ? " active" : "")));
    const text = element("span"); text.append(element("span","name",client.name), element("span","meta",client.signal.label+(client.band?` · ${client.band}`:"")));
    if(client.rssiSource==="shelly_wifi_status") {
      text.append(element("span","meta",t("rssi_shelly")+(client.rssiObservedAt?" · "+new Date(client.rssiObservedAt).toLocaleTimeString(this._language,{hour:"2-digit",minute:"2-digit",second:"2-digit"}):"")));
      if(client.googleQuality.key!=="unknown")text.append(element("span","meta",t("google_quality",{quality:client.googleQuality.label.replace(" · Google","")})));
      if(client.channel && client.bssid)text.append(element("span","meta",t("radio_details",{channel:client.channel,bssid:client.bssid})));
    }
    if(client.ip || client.mac)text.append(element("span","meta",[client.ip,client.mac].filter(Boolean).join(" · ")));
    const format=value=>typeof value==="number" && Number.isFinite(value)?new Intl.NumberFormat(this._language,{maximumFractionDigits:4}).format(value):"—";
    text.append(element("span","meta",client.download==null && client.upload==null?t("no_traffic"):t("traffic",{download:format(client.download),upload:format(client.upload)})));
    if(client.wifiTest!=null && client.wifiTestAt)text.append(element("span","meta",t("wifi_test",{speed:format(client.wifiTest),point:client.wifiTestPoint || t("unknown_point"),time:new Date(client.wifiTestAt).toLocaleString(this._language,{year:"numeric",month:"short",day:"2-digit",hour:"2-digit",minute:"2-digit"})})));
    const usage=client.usageWindows?.hour;
    if(usage)text.append(element("span","meta",t("usage_24h",{download:formatBytes(usage.complete?usage.download_bytes:null,this._language),upload:formatBytes(usage.complete?usage.upload_bytes:null,this._language)})));
    if(client.nameSource==="user")text.append(element("span","meta",t("user_name")));
    node.append(bars,text); node.addEventListener("click",() => this._moreInfo(client.entityId));
    const row=element("div","client-row"),actions=element("div","actions");row.append(node);
    if(client.roaming && client.ownDeviceId) {
      const link=element("a",null,t("roaming"));link.href="/config/devices/device/"+encodeURIComponent(client.ownDeviceId);actions.append(link);
    }
    if(client.metricsEntityId) {
      const metrics=element("button",null,t("metrics"));metrics.type="button";metrics.addEventListener("click",()=>this._moreInfo(client.metricsEntityId));actions.append(metrics);
    }
    if(actions.children.length)row.append(actions);
    if(client.controls?.length)row.append(this._controls(client.controls));
    if(client.usageWindows?.hour){const details=element("details");details.append(element("summary",null,t("history")));details.addEventListener("toggle",()=>{if(details.open && details.children.length===1)details.append(this._history(client,client.entityId));});row.append(details);}
    return row;
  }
  _informationPanel(key,label,markup) {
    this._informationPanels ||= new Map();
    const host=this._informationPanels.get(key)||element('div','gwi-information');
    this._informationPanels.set(key,host);this._usedInformation.add(key);
    renderInformation(host,`<details data-gwi-disclosure="${key.replace(/[&<>"']/g,'_')}">${informationSummary(label,this._language)}${markup}</details>`,key);
    return host;
  }
  _pointNode(p,scope) {
    const t=translate(this._language);
    const point=element("button","point"+(p.isRoot?" primary":"")); point.type="button"; point.dataset.entity=p.entityId; point.dataset.pointId=p.id;
    point.append(element("span","circle","AP"),element("span","name",p.name));
    const status=element("span","status");
    status.append(element("i","dot "+(p.online===true?"online":p.online===false?"offline":"")),document.createTextNode(p.unavailable?t("unavailable"):p.online===true?"Online":p.online===false?"Offline":t("unknown_status")));
    point.append(status,element("span","meta",p.isRoot?t("primary"):t("mesh_quality",{quality:p.mesh.label})),element("span","meta",p.count===null?t("no_clients_data"):t("observed_clients",{count:p.count})));
    if(p.ratedClients) point.append(element("span","meta",t("rated",{count:p.ratedClients})));
    const operationBadge=this._operationBadge(p.operation);if(operationBadge)point.append(operationBadge);
    if(p.weakClients) point.append(element("span","meta weak-count",t("weak_clients",{count:p.weakClients})));
    if(p.backhaul)point.append(element("span","meta",t("backhaul",{type:p.backhaul})));
    if(p.meshTest!=null && p.meshTestAt)point.append(element("span","meta",t("mesh_test",{speed:p.meshTest,time:new Date(p.meshTestAt).toLocaleString(this._language)})));
    point.addEventListener("click",()=>this._moreInfo(p.entityId));
    const wrapper=element("div");wrapper.append(point,this._controls(p.controls));
    if(p.firmwareInfo||p.lanInfo)wrapper.append(this._informationPanel(scope+":"+p.id,this._language==="pt"?"Firmware e informação LAN/WAN":"Firmware and LAN/WAN information",pointInformation(p,this._language,v=>new Date(v).toLocaleString(this._language,{timeZone:this._hass?.config?.time_zone}))));
    return wrapper;
  }
  _meshOverview(n) {
    const t=translate(this._language);
    const heading=element("div"); heading.append(element("h3",null,t("mesh_title")),element("p",null,t("mesh_description")));
    if(!n.root) { heading.append(element("p","empty",t("no_root"))); return heading; }
    const cluster=element("div","mesh-overview");
    cluster.append(element("p",null,t("primary")+" · "+n.root.name));
    const leaves=element("div","mesh-ratings");
    for(const link of n.meshLinks) {
      const p=n.points.find(p=>p.id===link.to),button=element("button","mesh-point "+link.quality.key); button.type="button"; button.dataset.entity=p.entityId; button.dataset.pointId=p.id;
      button.setAttribute("aria-label",t("mesh_details",{name:p.name,primary:n.root.name,quality:link.quality.label}));
      const bars=element("span","bars"); bars.setAttribute("aria-hidden","true");
      for(let i=0;i<4;i++)bars.append(element("span","bar"+(i<link.quality.bars?" active":"")));
      const text=element("span"); text.append(element("span","name",p.name),element("span","meta",t("compared_with",{name:n.root.name,quality:p.online===false?t("offline_no_rating"):link.quality.label})));
      button.append(bars,text); button.addEventListener("click",()=>this._moreInfo(p.entityId)); leaves.append(button);
    }
    if(!n.meshLinks.length)leaves.append(element("span","empty",t("no_satellites")));
    cluster.append(leaves);
    const peers=n.points.filter(p=>!p.isRoot);
    if(peers.length>1) {
      const details=element("details"),list=element("div","peer-list");details.append(element("summary",null,t("peer_links")));
      for(let i=0;i<peers.length;i++)for(let j=i+1;j<peers.length;j++)list.append(element("span",null,peers[i].name+" ↔ "+peers[j].name+" · "+t("peer_unknown")));
      details.append(list);cluster.append(details);
    }
    heading.append(cluster); return heading;
  }
  _render() {
    if(!this._config) return;
    const t=translate(this._language); this.lang=this._language;
    const active=this.shadowRoot.activeElement;
    this._usedInformation=new Set();
    this.shadowRoot.replaceChildren(element("style",null,CSS+informationCss));
    const card = element("ha-card"), content = element("div","content");
    const returnPath=overviewPath(this._config,window.location?.pathname || "");
    if(returnPath) {
      const back=element("a","back-link");back.href=returnPath;
      const arrow=element("span",null,"←");arrow.setAttribute("aria-hidden","true");
      back.append(arrow,document.createTextNode(t("back_overview")));content.append(back);
    }
    content.append(element("h2",null,this._config.title || t("title")));
    content.append(element("p",null,t("subtitle")));
    const legend = element("div","legend");
    for(const [key,label] of [["good","good_legend"],["fair","fair"],["weak","weak"],["unknown","no_measurement"]]) {
      const item = element("span",key); item.append(element("i","dot signal"),document.createTextNode(t(label))); legend.append(item);
    }
    content.append(legend);
    if(!this._model?.length) content.append(element("p","empty",t("no_entities")));
    for(const n of this._model || []) {
      const section = element("section","network"); section.append(element("h3",null,n.name));
      const operation=this._operationBanner(n.operation);if(operation)section.append(operation);
      section.append(element("p",null,t(n.unavailable?"query_unavailable":n.source==="local_status"?"local_mode":"connected_clients",{count:n.clients.length})));
      if(n.source!=="local_status") {
        const summary=element("div","summary"); summary.append(element("span",null,t("coverage",{count:n.ratedClients,total:n.clients.length})));
        summary.append(element("span",n.weakClients?"weak-count":"",t("weak_clients",{count:n.weakClients}))); section.append(summary,this._meshOverview(n));
        summary.append(element("span",null,t("real_rssi",{count:n.rssiClients})));
        if(n.controls?.length)section.append(this._controls(n.controls));
        if(n.usageHourly?.length && n.metricsEntityId)section.append(this._history(n,n.metricsEntityId));
        if(n.capabilitiesEntityId){const capability=element("button","more",t("capabilities"));capability.type="button";capability.addEventListener("click",()=>this._moreInfo(n.capabilitiesEntityId));section.append(capability);}
        if(n.operationEntityId){const operation=element("button","more",t("operation",{state:n.lastOperation}));operation.type="button";operation.addEventListener("click",()=>this._moreInfo(n.operationEntityId));section.append(operation);}
        if(n.wan_test_at) section.append(element("p",null,t("wan_test",{download:n.wan_test_download_mbps==null?"—":t.number(Number(n.wan_test_download_mbps)),upload:n.wan_test_upload_mbps==null?"—":t.number(Number(n.wan_test_upload_mbps)),time:new Date(n.wan_test_at).toLocaleString(this._language)})));
        if(n.metricsEntityId) {const metrics=element("button","more",t("metrics"));metrics.type="button";metrics.addEventListener("click",()=>this._moreInfo(n.metricsEntityId));section.append(metrics);}
        if(n.clients.some(c=>c.roaming))section.append(element("p",null,t("roaming_hint")));
      }
      section.append(element("h3",null,t("client_groups")));
      if(n.networkInfo)section.append(this._informationPanel(n.scope+":network",this._language==="pt"?"Configuração LAN/WAN":"LAN/WAN configuration",networkInformation(n,this._language,v=>new Date(v).toLocaleString(this._language,{timeZone:this._hass?.config?.time_zone}))));
      for(const p of n.points) {
        const cluster = element("div","cluster");
        const svg = document.createElementNS("http://www.w3.org/2000/svg","svg"); svg.classList.add("edges"); svg.setAttribute("aria-hidden","true"); cluster.append(svg);
        cluster.append(this._pointNode(p,n.scope));
        const clients = element("div","clients"), expanded = this._expanded.has(n.scope+":"+p.id);
        for(const client of p.clients.slice(0,expanded ? undefined : this._config.max_clients)) clients.append(this._clientNode(client));
        if(p.clients.length > this._config.max_clients) {
          const button = element("button","more",expanded ? t("collapse") : t("more",{count:p.clients.length-this._config.max_clients})); button.type="button";
          button.addEventListener("click",()=>{const key=n.scope+":"+p.id; expanded ? this._expanded.delete(key) : this._expanded.add(key); this._render();}); clients.append(button);
        }
        if(!p.clients.length) clients.append(element("span","empty",t(n.source==="local_status"?"local_associations":p.unavailable || n.unavailable?"no_observation":"no_associations")));
        cluster.append(clients); section.append(cluster);
      }
      if(n.unassigned.length) {
        const group=element("div","unassigned"); group.append(element("h3",null,t("unassigned")));
        const clients=element("div","clients"); for(const client of n.unassigned) clients.append(this._clientNode(client)); group.append(clients); section.append(group);
      }
      content.append(section);
    }
    content.append(element("p",null,t("limits")));
    const metadata=window.customCards?.find(card=>card.type==="google-wifi-insights-map");
    if(metadata)metadata.description=t("card_description");
    card.append(content); this.shadowRoot.append(card);
    for(const key of this._informationPanels?.keys()||[])if(!this._usedInformation.has(key))this._informationPanels.delete(key);
    if(active?.isConnected)active.focus({preventScroll:true});
    cancelAnimationFrame(this._frame); this._frame=requestAnimationFrame(()=>this._drawEdges());
  }
  _drawEdges() {
    for(const cluster of this.shadowRoot.querySelectorAll(".cluster")) {
      const svg=cluster.querySelector("svg"), point=cluster.querySelector(".point"), r=cluster.getBoundingClientRect(), pr=point.getBoundingClientRect();
      if(!r.width) continue;
      svg.setAttribute("viewBox",`0 0 ${r.width} ${r.height}`); svg.replaceChildren();
      const clients=[...cluster.querySelectorAll('.client,.mesh-point')];
      if(!clients.length) continue;
      const first=clients[0].getBoundingClientRect(), stacked=first.top>=pr.bottom;
      const sx=(stacked?pr.left+pr.width/2:pr.right)-r.left, sy=(stacked?pr.bottom:pr.top+pr.height/2)-r.top;
      const trunkX=stacked?8:(sx+first.left-r.left)/2;
      const ys=clients.map(c=>{const cr=c.getBoundingClientRect();return cr.top+cr.height/2-r.top;});
      const trunk=document.createElementNS('http://www.w3.org/2000/svg','path');
      trunk.setAttribute('d',stacked?`M ${sx} ${sy} V ${sy+12} H ${trunkX} V ${Math.max(...ys)}`:`M ${sx} ${sy} H ${trunkX} M ${trunkX} ${Math.min(sy,...ys)} V ${Math.max(sy,...ys)}`);
      trunk.setAttribute('class','trunk');trunk.style.stroke='var(--divider-color)';svg.append(trunk);
      for(const client of clients) {
        const cr=client.getBoundingClientRect();
        const tx=cr.left-r.left, ty=cr.top+cr.height/2-r.top;
        const path=document.createElementNS("http://www.w3.org/2000/svg","path");
        path.setAttribute("d",`M ${trunkX} ${ty} H ${tx}`);
        path.setAttribute("class",["excellent","good","fair","weak"].find(k=>client.classList.contains(k)) || "unknown"); svg.append(path);
        path.dataset.from=point.dataset.pointId; path.dataset.to=client.dataset.pointId || client.dataset.entity;
      }
    }
  }
}

if(!customElements.get("google-wifi-insights-map")) customElements.define("google-wifi-insights-map",GoogleWifiInsightsMap);
window.customCards = window.customCards || [];
if(!window.customCards.some(card=>card.type==="google-wifi-insights-map")) window.customCards.push({type:"google-wifi-insights-map", name:"Google WiFi Insights", description:translate("en")("card_description"), preview:false});
