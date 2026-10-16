// Management uses HA services and cached discovery. No provider credentials enter the UI.
import {languageOf,mapModel,operationFeedback} from './gwi-map-model.js?v=0.10.0';

const WORDS={
 en:{title:'Network management',intro:'Map Wi-Fi points to Home Assistant areas and launch network actions.',network:'Network',refresh:'Refresh view',loading:'Loading management…',empty:'Connect a Google account to manage a network.',admin:'A Home Assistant administrator is required to manage this network.',failed:'Management is unavailable. Check the integration and try refreshing.',unavailable:'This network is unavailable. Wait for a successful update.',areas:'Points and areas',areaLabel:'Area',areaHint:'Each device gets a WiFi associated area sensor, based on its current wireless point. This estimates the area; it does not change the fixed device area in Home Assistant.',unmapped:'No area mapped',save:'Save area',saved:'Area mapping saved.',online:'Online',offline:'Offline or unknown',names:'Review unnamed devices',nameHint:'Suggestions use an exact MAC match with Home Assistant. Personalized Google names and ambiguous matches are preserved.',nameLimit:'Automatic renaming in Google is not available in this version. Copy a suggested name and apply it in Google Home → Wi-Fi → Devices → device → Edit. Refresh after Google discovery updates.',noNames:'No unnamed devices with an unambiguous HA MAC match.',proposed:'Suggested HA name',google:'Google name',copy:'Copy suggested name',copied:'Name copied. Apply it in Google Home.',copyFailed:'Copy unavailable. Select and copy the suggested name below.',guide:'Google naming instructions',actions:'Quick actions',actionHint:'Requests are sent only after confirmation. Tests may affect throughput; restarts temporarily interrupt connectivity.',restart_network:'Restart network',restart_point:'Restart point',test_internet:'Test Internet speed',test_mesh:'Test mesh to primary',test_local:'Test local speed',test_clients:'Test WiFi clients',confirm:'Confirm request',cancel:'Cancel',confirmHint:'Send this request to the selected target?',sending:'Sending request…',accepted:'Google accepted the request. Completion is not yet confirmed.',completed:'Google reports the operation completed.',unconfirmed:'The result is unconfirmed. Check the action status before sending again.',actionFailed:'The request failed or its delivery is unconfirmed. Check the action status before sending again.',latest:'Latest operation',status:'Status',primary:'Primary point',selectName:'Suggested device name'},
 pt:{title:'Gestão da rede',intro:'Mapeie os points às divisões do Home Assistant e execute ações na rede.',network:'Rede',refresh:'Atualizar vista',loading:'A carregar gestão…',empty:'Ligue uma conta Google para gerir uma rede.',admin:'A gestão desta rede requer um administrador do Home Assistant.',failed:'Gestão indisponível. Verifique a integração e atualize a vista.',unavailable:'Esta rede está indisponível. Aguarde uma atualização bem-sucedida.',areas:'Points e divisões',areaLabel:'Divisão',areaHint:'Cada dispositivo recebe um sensor de divisão associada ao Wi-Fi, baseado no point atual. É uma estimativa da divisão; não altera a divisão fixa do dispositivo no Home Assistant.',unmapped:'Sem divisão mapeada',save:'Guardar divisão',saved:'Associação à divisão guardada.',online:'Online',offline:'Offline ou desconhecido',names:'Rever dispositivos sem nome',nameHint:'As sugestões usam uma correspondência exata de MAC com o Home Assistant. Nomes Google personalizados e correspondências ambíguas são preservados.',nameLimit:'A renomeação automática na Google ainda não está disponível nesta versão. Copie a sugestão e aplique-a em Google Home → Wi-Fi → Dispositivos → dispositivo → Editar. Atualize a vista após a descoberta Google.',noNames:'Sem dispositivos sem nome com uma correspondência MAC inequívoca no HA.',proposed:'Nome HA sugerido',google:'Nome Google',copy:'Copiar nome sugerido',copied:'Nome copiado. Aplique-o no Google Home.',copyFailed:'Não foi possível copiar. Selecione e copie o nome sugerido abaixo.',guide:'Instruções Google para os nomes',actions:'Ações rápidas',actionHint:'Os pedidos só são enviados após confirmação. Os testes podem afetar o débito; os reinícios interrompem temporariamente a ligação.',restart_network:'Reiniciar rede',restart_point:'Reiniciar point',test_internet:'Testar velocidade da Internet',test_mesh:'Testar mesh até ao principal',test_local:'Testar velocidade local',test_clients:'Testar clientes WiFi',confirm:'Confirmar pedido',cancel:'Cancelar',confirmHint:'Enviar este pedido ao destino selecionado?',sending:'A enviar pedido…',accepted:'A Google aceitou o pedido. A conclusão ainda não foi confirmada.',completed:'A Google indica que a operação terminou.',unconfirmed:'O resultado não foi confirmado. Verifique o estado da ação antes de repetir.',actionFailed:'O pedido falhou ou a entrega não foi confirmada. Verifique o estado da ação antes de repetir.',latest:'Última operação',status:'Estado',primary:'Point principal',selectName:'Nome sugerido do dispositivo'},
};
const node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
const button=(text,action)=>{const n=node('button',text);n.type='button';n.addEventListener('click',action);return n;};
const CSS=`:host{display:block;padding:20px;color:var(--primary-text-color);font:14px/1.5 var(--paper-font-body1_-_font-family,system-ui)}h1{font-size:24px;margin:0}h2{font-size:19px;margin:0 0 8px}h3{font-size:16px;margin:0}p{color:var(--secondary-text-color);margin:6px 0 14px;max-width:85ch}.toolbar,.buttons{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.toolbar{margin:20px 0}.toolbar label{display:grid;gap:4px;min-width:220px}section{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:16px;padding:20px;margin:18px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:14px}.point,.candidate,.action-target{border:1px solid var(--divider-color);border-radius:12px;padding:16px;min-width:0;overflow-wrap:anywhere}.point label{display:grid;gap:6px;margin:10px 0}.candidate{margin-top:10px}.candidate input{width:100%;box-sizing:border-box;margin:6px 0 12px}.meta{font-size:12px;color:var(--secondary-text-color)}button,select,input{font:inherit;color:inherit;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);padding:9px 12px;min-height:42px;max-width:100%}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,select:focus-visible,input:focus-visible,a:focus-visible{outline:3px solid var(--primary-color);outline-offset:2px}.primary{background:var(--primary-color);color:var(--text-primary-color,#fff);border-color:transparent}.notice{background:var(--secondary-background-color);border-radius:10px;padding:12px}.feedback{white-space:pre-line;overflow-wrap:anywhere}.confirmation{border:2px solid var(--primary-color);padding:16px;border-radius:12px;margin:12px 0}.confirmation p{color:inherit}a{color:var(--primary-color)}[hidden]{display:none!important}@media(max-width:500px){:host{padding:12px}section{padding:14px}.toolbar label{min-width:0;width:100%}.buttons button{flex:1 1 120px}}`;

export class GwiManagement extends HTMLElement {
 constructor(){super();this.attachShadow({mode:'open'});this._generation=0;this._drafts=new Map();}
 setConfig(value){this._config=value||{};}
 connectedCallback(){this._connected=true;if(this._hass)this._update();}
 disconnectedCallback(){this._connected=false;this._generation++;this._loading=false;this._attempted=false;}
 set hass(value){this._hass=value;if(this._connected)this._update();}
 _update(){
  const language=languageOf(this._hass),admin=this._hass?.user?.is_admin===true;
  if(language!==this._language||!this._built){this._language=language;this._build();}
  this._admin=admin;
  const networks=mapModel(this._hass?.states).filter(n=>n.source==='google_cloud');
  const signature=JSON.stringify(networks.map(n=>[n.scope,n.name]));
  if(signature!==this._networksSignature){
   this._networksSignature=signature;this._selector.replaceChildren();
   for(const n of networks){const option=node('option',n.name);option.value=n.scope;this._selector.append(option);}
  }
  this._networks=networks;
  if(!networks.some(n=>n.scope===this._scope))this._changeScope(networks[0]?.scope);
  this._selector.value=this._scope||'';
  const network=this._network();
  this._selector.disabled=this._busy||!admin;
  this._refresh.disabled=this._busy||this._loading||!admin||!network||network.unavailable;
  if(!admin||!network||network.unavailable){
   this._generation++;this._loading=false;this._data=null;this._attempted=false;this._confirmation=null;this._content.replaceChildren();
   this._say(!admin?'admin':!network?'empty':'unavailable');return;
  }
  if(!this._data&&!this._loading&&!this._attempted)this._load();
  this._updateFeedback();this._updateDisabled();
 }
 _network(){return this._networks?.find(n=>n.scope===this._scope);}
 _build(){
  this._built=true;this._networksSignature=null;this._confirmation=null;
  this.shadowRoot.replaceChildren(node('style',CSS),node('h1',this._t('title')),node('p',this._t('intro')));
  const toolbar=node('div');toolbar.className='toolbar';const label=node('label',this._t('network'));
  this._selector=node('select');this._selector.addEventListener('change',()=>{this._changeScope(this._selector.value);this._update();});
  label.append(this._selector);this._refresh=button(this._t('refresh'),()=>this._load());toolbar.append(label,this._refresh);
  this._status=node('p');this._status.setAttribute('role','status');this._status.setAttribute('aria-live','polite');
  this._content=node('div');this.shadowRoot.append(toolbar,this._status,this._content);
  this._say(this._message);
  if(this._data)this._renderContent();
 }
 _t(key){return WORDS[this._language||'en'][key]||key;}
 _say(key){this._message=key;this._status.textContent=key?this._t(key):'';}
 _changeScope(scope){this._scope=scope;this._generation++;this._data=null;this._loading=false;this._attempted=false;this._confirmation=null;this._content.replaceChildren();this._say(null);}
 async _call(service,data){const result=await this._hass.callWS({type:'call_service',domain:'google_wifi_insights',service,service_data:data,return_response:true});return result.response;}
 async _load(){
  const network=this._network();if(!this._admin||!network||network.unavailable||this._busy)return;
  const request=++this._generation,scope=this._scope;this._attempted=true;this._loading=true;this._say('loading');this._refresh.disabled=true;
  try{const data=await this._call('get_management',{entity_id:network.entityId});
   if(request!==this._generation||!this._connected)return;
   if(data?.scope!==scope||!Array.isArray(data.points)||!Array.isArray(data.areas)||!Array.isArray(data.name_candidates))throw Error('Invalid management response');
   this._data=data;this._confirmation=null;this._say(null);this._renderContent();
  }catch{if(request===this._generation)this._say('failed');}
  finally{if(request===this._generation){this._loading=false;this._updateDisabled();}}
 }
 _section(title,hint){const section=node('section');section.append(node('h2',this._t(title)),node('p',this._t(hint)));this._content.append(section);return section;}
 _renderContent(){
  this._content.replaceChildren();if(!this._data)return;
  const areas=this._section('areas','areaHint'),grid=node('div');grid.className='grid';areas.append(grid);
  for(const point of this._data.points){
   const card=node('div');card.className='point';card.append(node('h3',point.name));const meta=node('p',point.online===true?this._t('online'):this._t('offline'));meta.className='meta';card.append(meta);
   const label=node('label',this._t('areaLabel')),select=node('select');select.dataset.point=point.id;select.setAttribute('aria-label',this._t('areaLabel')+' · '+point.name);
   for(const area of [{id:'',name:this._t('unmapped')},...this._data.areas]){const option=node('option',area.name);option.value=area.id;select.append(option);}
   const key=this._scope+':'+point.id;select.value=this._drafts.has(key)?this._drafts.get(key):point.area_id||'';
   select.addEventListener('change',()=>this._drafts.set(key,select.value));label.append(select);
   const save=button(this._t('save'),()=>this._saveArea(point,select.value));save.className='primary';save.dataset.write='area';save.dataset.entity=point.entity_id||'';
   card.append(label,save);grid.append(card);
  }
  const names=this._section('names','nameHint'),limit=node('p',this._t('nameLimit'));limit.className='notice';names.append(limit);
  const guide=node('a',this._t('guide'));guide.href='https://support.google.com/googlehome/answer/6346150';guide.target='_blank';guide.rel='noopener noreferrer';names.append(guide);
  if(!this._data.name_candidates.length)names.append(node('p',this._t('noNames')));
  for(const candidate of this._data.name_candidates){
   const row=node('div');row.className='candidate';row.append(node('h3',candidate.proposed_name),node('p',this._t('google')+': '+candidate.google_name));
   const meta=node('p',candidate.mac_address);meta.className='meta';row.append(meta);const label=node('label',this._t('proposed')),input=node('input');input.readOnly=true;input.value=candidate.proposed_name;input.setAttribute('aria-label',this._t('selectName'));label.append(input);row.append(label,button(this._t('copy'),async()=>{
    try{await navigator.clipboard.writeText(candidate.proposed_name);this._say('copied');}catch{input.focus();input.select();this._say('copyFailed');}
   }));names.append(row);
  }
  const actions=this._section('actions','actionHint');this._confirmHost=node('div');actions.append(this._confirmHost);
  const targets=node('div');targets.className='grid';actions.append(targets);
  this._feedbackNodes=[];
  for(const target of [{id:this._data.network_id,name:this._data.name,entity_id:this._data.entity_id,kind:'network'},...this._data.points.map(p=>({...p,kind:'point'}))]){
   const card=node('div');card.className='action-target';card.append(node('h3',target.name));const buttons=node('div');buttons.className='buttons';card.append(buttons);
   const keys=target.kind==='network'?['test_internet','restart_network']:['test_local','test_clients',...(!target.is_root?['test_mesh']:[]),'restart_point'];
   for(const action of keys){const b=button(this._t(action),()=>this._confirm(target,action));b.dataset.action=action;b.dataset.target=target.id;b.dataset.write='action';b.dataset.entity=target.entity_id||'';buttons.append(b);}
   const feedback=node('p');feedback.className='feedback';feedback.setAttribute('role','status');card.append(feedback);this._feedbackNodes.push({target,node:feedback});targets.append(card);
  }
  this._updateFeedback();this._updateDisabled();
 }
 _updateDisabled(){
  const network=this._network(),disabled=this._busy||!this._admin||!network||network.unavailable||this._loading;
  this._refresh.disabled=Boolean(disabled);this._selector.disabled=Boolean(this._busy||!this._admin);
  for(const b of this._content.querySelectorAll('button[data-write]')){
   const target=b.dataset.target===this._data?.network_id?network:network?.points.find(p=>p.id===b.dataset.target),operation=target?.operation;
   const pending=operation?.action===b.dataset.action&&['queued','sending','accepted','running'].includes(operation?.phase);
   b.disabled=Boolean(disabled||!b.dataset.entity||pending);
  }
  for(const select of this._content.querySelectorAll('select'))select.disabled=Boolean(disabled);
 }
 async _saveArea(point,area_id){
  if(this._busy||!this._admin||this._network()?.unavailable||!point.entity_id)return;
  this._busy=true;const generation=this._generation,scope=this._scope;this._updateDisabled();
  try{const data=await this._call('set_point_area',{entity_id:point.entity_id,area_id:area_id||null});
   if(generation!==this._generation||!this._connected)return;
   if(data?.scope!==scope)throw Error('Wrong network');
   this._drafts.delete(scope+':'+point.id);this._data=data;this._say('saved');this._renderContent();
  }catch{if(generation===this._generation)this._say('failed');}
  finally{this._busy=false;this._updateDisabled();}
 }
 _confirm(target,action){
  if(this._busy||!this._admin||this._network()?.unavailable||!target.entity_id)return;
  this._confirmation={target,action};this._confirmHost.replaceChildren();const box=node('div');box.className='confirmation';box.setAttribute('role','group');
  box.append(node('strong',this._t(action)+' · '+target.name+' · '+this._data.name),node('p',this._t('confirmHint')));
  const confirm=button(this._t('confirm'),()=>this._execute()),cancel=button(this._t('cancel'),()=>{this._confirmation=null;this._confirmHost.replaceChildren();});confirm.className='primary';
  box.append(confirm,cancel);this._confirmHost.append(box);confirm.focus();
 }
 async _execute(){
  const request=this._confirmation;if(!request||this._busy||!this._admin||this._network()?.unavailable)return;
  this._confirmation=null;this._confirmHost.replaceChildren();this._busy=true;this._say('sending');this._updateDisabled();const generation=this._generation;
  try{const result=await this._call('google_action',{entity_id:request.target.entity_id,action:request.action});
   if(generation!==this._generation||!this._connected)return;
   this._say(result?.state==='DONE'?'completed':['CREATED','RUNNING','PENDING','QUEUED'].includes(result?.state)?'accepted':'unconfirmed');
  }catch{if(generation===this._generation)this._say('actionFailed');}
  finally{this._busy=false;this._updateDisabled();}
 }
 _updateFeedback(){
  const network=this._network();
  for(const item of this._feedbackNodes||[]){
   const target=item.target.kind==='network'?network:network?.points.find(p=>p.id===item.target.id);
   const feedback=operationFeedback(target?.operation,this._language);
   item.node.textContent=feedback?this._t('latest')+': '+feedback.actionLabel+' · '+feedback.label+'\n'+feedback.note:'';
  }
 }
}
if(!customElements.get('google-wifi-management'))customElements.define('google-wifi-management',GwiManagement);
