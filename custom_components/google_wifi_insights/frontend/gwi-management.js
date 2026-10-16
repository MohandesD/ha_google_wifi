// Management uses HA services and cached discovery. No provider credentials enter the UI.
import {languageOf,mapModel,operationFeedback,isLocalHaPath} from './gwi-map-model.js?v=0.12.1';

const WORDS={
 en:{title:'Network management',intro:'Map Wi-Fi points to Home Assistant areas and launch network actions.',network:'Network',refresh:'Refresh view',loading:'Loading management…',empty:'Connect a Google account to manage a network.',admin:'A Home Assistant administrator is required to manage this network.',failed:'Management is unavailable. Check the integration and try refreshing.',unavailable:'This network is unavailable. Wait for a successful update.',areas:'Points and areas',areaLabel:'Area',areaHint:'Each device gets a WiFi associated area sensor, based on its current wireless point. This estimates the area; it does not change the fixed device area in Home Assistant.',unmapped:'No area mapped',save:'Save area',saved:'Area mapping saved.',online:'Online',offline:'Offline or unknown',names:'Review unnamed devices',nameHint:'Suggestions use an exact MAC match with Home Assistant. Personalized Google names and ambiguous matches are preserved.',nameLimit:'Automatic naming starts disabled.',noNames:'No unnamed devices with an unambiguous HA MAC match.',proposed:'Suggested HA name',google:'Google name',copy:'Copy suggested name',copied:'Name copied. Apply it in Google Home.',copyFailed:'Copy unavailable. Select and copy the suggested name below.',guide:'Google naming instructions',actions:'Quick actions',actionHint:'Requests are sent only after confirmation. Tests may affect throughput; restarts temporarily interrupt connectivity.',restart_network:'Restart network',restart_point:'Restart point',test_internet:'Test Internet speed',test_mesh:'Test mesh to primary',test_local:'Test local speed',test_clients:'Test WiFi clients',confirm:'Confirm request',cancel:'Cancel',confirmHint:'Send this request to the selected target?',sending:'Sending request…',accepted:'Google accepted the request. Completion is not yet confirmed.',completed:'Google reports the operation completed.',unconfirmed:'The result is unconfirmed. Check the action status before sending again.',actionFailed:'The request failed or its delivery is unconfirmed. Check the action status before sending again.',latest:'Latest operation',status:'Status',primary:'Primary point',selectName:'Suggested device name'},
 pt:{title:'Gestão da rede',intro:'Mapeie os points às divisões do Home Assistant e execute ações na rede.',network:'Rede',refresh:'Atualizar vista',loading:'A carregar gestão…',empty:'Ligue uma conta Google para gerir uma rede.',admin:'A gestão desta rede requer um administrador do Home Assistant.',failed:'Gestão indisponível. Verifique a integração e atualize a vista.',unavailable:'Esta rede está indisponível. Aguarde uma atualização bem-sucedida.',areas:'Points e divisões',areaLabel:'Divisão',areaHint:'Cada dispositivo recebe um sensor de divisão associada ao Wi-Fi, baseado no point atual. É uma estimativa da divisão; não altera a divisão fixa do dispositivo no Home Assistant.',unmapped:'Sem divisão mapeada',save:'Guardar divisão',saved:'Associação à divisão guardada.',online:'Online',offline:'Offline ou desconhecido',names:'Rever dispositivos sem nome',nameHint:'As sugestões usam uma correspondência exata de MAC com o Home Assistant. Nomes Google personalizados e correspondências ambíguas são preservados.',nameLimit:'A renomeação automática começa desativada.',noNames:'Sem dispositivos sem nome com uma correspondência MAC inequívoca no HA.',proposed:'Nome HA sugerido',google:'Nome Google',copy:'Copiar nome sugerido',copied:'Nome copiado. Aplique-o no Google Home.',copyFailed:'Não foi possível copiar. Selecione e copie o nome sugerido abaixo.',guide:'Instruções Google para os nomes',actions:'Ações rápidas',actionHint:'Os pedidos só são enviados após confirmação. Os testes podem afetar o débito; os reinícios interrompem temporariamente a ligação.',restart_network:'Reiniciar rede',restart_point:'Reiniciar point',test_internet:'Testar velocidade da Internet',test_mesh:'Testar mesh até ao principal',test_local:'Testar velocidade local',test_clients:'Testar clientes WiFi',confirm:'Confirmar pedido',cancel:'Cancelar',confirmHint:'Enviar este pedido ao destino selecionado?',sending:'A enviar pedido…',accepted:'A Google aceitou o pedido. A conclusão ainda não foi confirmada.',completed:'A Google indica que a operação terminou.',unconfirmed:'O resultado não foi confirmado. Verifique o estado da ação antes de repetir.',actionFailed:'O pedido falhou ou a entrega não foi confirmada. Verifique o estado da ação antes de repetir.',latest:'Última operação',status:'Estado',primary:'Point principal',selectName:'Nome sugerido do dispositivo'},
};
const node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
Object.assign(WORDS.en,{nameLimit:'Optional automatic naming changes only generic Google names with an exact HA MAC match. Existing personalized names are preserved. Changes are verified by reading Google again. Automatic naming starts disabled.',enableNames:'Enable automatic naming',disableNames:'Disable automatic naming',resumeNames:'Resume automatic naming',applyName:'Apply name in Google',undoName:'Undo name change',verifyName:'Verify result',recentNames:'Recent name changes',nameConfirm:'This changes device display names in the selected Google Home network. Only generic names with an unambiguous HA MAC match are eligible.',nameSaved:'Name change verified in Google.',nameUnconfirmed:'The name change is unconfirmed. Use Verify result; the request will not be repeated automatically.',nameRejected:'Google rejected the request. Automatic naming is paused.',namesEnabled:'Automatic naming enabled for this network.',namesDisabled:'Automatic naming disabled for this network.',namesStatus:'Automatic naming',enabled:'Enabled',disabled:'Disabled',paused:'Paused',verified:'Verified',unconfirmed:'Awaiting verification',rejected:'Rejected',cancelled:'Cancelled',idle:'Idle',renamedCount:'Verified changes',pendingCount:'Awaiting verification',refreshNames:'Refresh view to review the latest name changes.'});
Object.assign(WORDS.pt,{nameLimit:'A renomeação automática opcional altera apenas nomes Google genéricos com correspondência MAC exata no HA. Os nomes personalizados são preservados. Cada alteração é confirmada com uma nova leitura da Google. A opção começa desativada.',enableNames:'Ativar renomeação automática',disableNames:'Desativar renomeação automática',resumeNames:'Retomar renomeação automática',applyName:'Aplicar nome na Google',undoName:'Desfazer alteração de nome',verifyName:'Verificar resultado',recentNames:'Alterações de nomes recentes',nameConfirm:'Esta ação altera os nomes apresentados na rede Google Home selecionada. Só são elegíveis nomes genéricos com correspondência MAC inequívoca no HA.',nameSaved:'Alteração de nome confirmada na Google.',nameUnconfirmed:'A alteração do nome não está confirmada. Use Verificar resultado; o pedido não será repetido automaticamente.',nameRejected:'A Google rejeitou o pedido. A renomeação automática está em pausa.',namesEnabled:'Renomeação automática ativada nesta rede.',namesDisabled:'Renomeação automática desativada nesta rede.',namesStatus:'Renomeação automática',enabled:'Ativada',disabled:'Desativada',paused:'Em pausa',verified:'Confirmada',unconfirmed:'A aguardar confirmação',rejected:'Rejeitada',cancelled:'Cancelada',idle:'Sem alterações',renamedCount:'Alterações confirmadas',pendingCount:'A aguardar confirmação',refreshNames:'Atualize a vista para rever as alterações de nomes mais recentes.'});
Object.assign(WORDS.en,{nameUndoConfirm:'Restore the previous Google label after checking the current name and MAC. This client will be excluded from future automatic naming.',nameExcluded:'Excluded from automatic naming after undo. You can still apply this suggestion manually.'});
Object.assign(WORDS.pt,{nameUndoConfirm:'Restaurar o nome Google anterior após confirmar o nome e MAC atuais. Este cliente ficará excluído de futuras renomeações automáticas.',nameExcluded:'Excluído da renomeação automática após desfazer. Pode aplicar esta sugestão manualmente.'});
Object.assign(WORDS.en,{manualNames:'Rename now',manualHint:'Rename selected suggestions or all eligible suggestions once, without enabling automatic naming.',selectDevice:'Select device',selectAll:'Select all eligible devices',selectionCount:'{selected} of {eligible} eligible devices selected',renameSelected:'Rename selected',renameAll:'Rename all eligible',batchHint:'Review every proposed change below. Requests run one at a time and stop on a rejected or unconfirmed result. This does not enable automatic naming. Keep this page open until the batch finishes.',batchDevices:'{count} devices',batchRunning:'Renaming {current} of {total} · {name}',batchSummary:'{verified} verified · {skipped} skipped · {remaining} not sent',batchComplete:'One-time renaming finished.',batchStopped:'One-time renaming stopped. Review the results before starting another batch.',batchProgress:'One-time rename progress',stopBatch:'Stop after current device',batchStopping:'Stopping after the current device. Its request may still complete.',skipped:'Preview changed; no request sent',sendingName:'Sending and verifying',notSent:'Not sent'});
Object.assign(WORDS.pt,{manualNames:'Renomear agora',manualHint:'Renomeie uma vez as sugestões selecionadas ou todas as elegíveis, sem ativar a renomeação automática.',selectDevice:'Selecionar dispositivo',selectAll:'Selecionar todos os dispositivos elegíveis',selectionCount:'{selected} de {eligible} dispositivos elegíveis selecionados',renameSelected:'Renomear selecionados',renameAll:'Renomear todos os elegíveis',batchHint:'Reveja cada alteração abaixo. Os pedidos são enviados um de cada vez e param se houver rejeição ou falta de confirmação. Isto não ativa a renomeação automática. Mantenha esta página aberta até terminar.',batchDevices:'{count} dispositivos',batchRunning:'A renomear {current} de {total} · {name}',batchSummary:'{verified} confirmados · {skipped} ignorados · {remaining} não enviados',batchComplete:'Renomeação pontual terminada.',batchStopped:'Renomeação pontual interrompida. Reveja os resultados antes de iniciar outro lote.',batchProgress:'Progresso da renomeação pontual',stopBatch:'Parar após o dispositivo atual',batchStopping:'A parar após o dispositivo atual. O pedido em curso ainda pode terminar.',skipped:'A sugestão mudou; nenhum pedido enviado',sendingName:'A enviar e verificar',notSent:'Não enviado'});
const button=(text,action)=>{const n=node('button',text);n.type='button';n.addEventListener('click',action);return n;};
Object.assign(WORDS.en,{batchHint:'Review every proposed change below. Up to {limit} devices run at once, with individual identity checks and verification. New requests stop on a rejected or unconfirmed result; requests already in progress may still complete. This does not enable automatic naming. Keep this page open until the batch finishes.',batchWorking:'{active} in progress · {done} of {total} checked',batchSummary:'{verified} verified · {active} in progress · {skipped} skipped · {review} to review · {remaining} not sent',stopBatch:'Stop pending requests',batchStopping:'Stopping new requests. {active} requests are still in progress and may complete.',batchConcurrency:'Up to {limit} devices at once',batchUpgrade:'The installed backend supports one device at a time. Update the complete integration for parallel renaming.',batchRefreshFailed:'Could not refresh the verified management view. Remaining requests were not sent.'});
Object.assign(WORDS.pt,{batchHint:'Reveja cada alteração abaixo. São processados até {limit} dispositivos em simultâneo, com validação da identidade e confirmação individuais. Novos pedidos param se houver rejeição ou falta de confirmação; os que já estão em curso podem terminar. Isto não ativa a renomeação automática. Mantenha esta página aberta até terminar.',batchWorking:'{active} em curso · {done} de {total} verificados',batchSummary:'{verified} confirmados · {active} em curso · {skipped} ignorados · {review} para rever · {remaining} não enviados',stopBatch:'Parar pedidos pendentes',batchStopping:'A parar novos pedidos. Existem {active} pedidos em curso que ainda podem terminar.',batchConcurrency:'Até {limit} dispositivos em simultâneo',batchUpgrade:'O backend instalado suporta um dispositivo de cada vez. Atualize a integração completa para renomear em paralelo.',batchRefreshFailed:'Não foi possível atualizar a vista de gestão confirmada. Os pedidos restantes não foram enviados.'});
const CSS=`:host{display:block;padding:20px;color:var(--primary-text-color);font:14px/1.5 var(--paper-font-body1_-_font-family,system-ui)}h1{font-size:24px;margin:0}h2{font-size:19px;margin:0 0 8px}h3{font-size:16px;margin:0}p{color:var(--secondary-text-color);margin:6px 0 14px;max-width:85ch}.toolbar,.buttons{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.toolbar{margin:20px 0}.toolbar label{display:grid;gap:4px;min-width:220px}section{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:16px;padding:20px;margin:18px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:14px}.point,.candidate,.action-target{border:1px solid var(--divider-color);border-radius:12px;padding:16px;min-width:0;overflow-wrap:anywhere}.point label{display:grid;gap:6px;margin:10px 0}.candidate{margin-top:10px}.candidate input{width:100%;box-sizing:border-box;margin:6px 0 12px}.meta{font-size:12px;color:var(--secondary-text-color)}button,select,input{font:inherit;color:inherit;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);padding:9px 12px;min-height:42px;max-width:100%}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,select:focus-visible,input:focus-visible,a:focus-visible{outline:3px solid var(--primary-color);outline-offset:2px}.primary{background:var(--primary-color);color:var(--text-primary-color,#fff);border-color:transparent}.notice{background:var(--secondary-background-color);border-radius:10px;padding:12px}.feedback{white-space:pre-line;overflow-wrap:anywhere}.confirmation{border:2px solid var(--primary-color);padding:16px;border-radius:12px;margin:12px 0}.confirmation p{color:inherit}a{color:var(--primary-color)}[hidden]{display:none!important}@media(max-width:500px){:host{padding:12px}section{padding:14px}.toolbar label{min-width:0;width:100%}.buttons button{flex:1 1 120px}}`;

export class GwiManagement extends HTMLElement {
 constructor(){super();this.attachShadow({mode:'open'});this._generation=0;this._drafts=new Map();this._selectedNames=new Map();}
 setConfig(value){if(value?.locations_path!=null&&!isLocalHaPath(value.locations_path))throw Error('locations_path must be a local HA path');this._config=value||{};if(this._connected&&this._hass)this._update();}
 connectedCallback(){this._connected=true;if(this._hass)this._update();}
 disconnectedCallback(){this._connected=false;this._generation++;this._loading=false;this._attempted=false;if(this._batch)this._batch.stopRequested=true;}
 set hass(value){this._hass=value;if(this._connected)this._update();}
 _update(){
  const language=languageOf(this._hass),admin=this._hass?.user?.is_admin===true;
  if(language!==this._language||!this._built){this._language=language;this._build();}
  this._admin=admin;
  const networks=mapModel(this._hass?.states,this._config).filter(n=>n.source==='google_cloud');
  const signature=JSON.stringify(networks.map(n=>[n.scope,n.name,n.locationName]));
  if(signature!==this._networksSignature){
   this._networksSignature=signature;this._selector.replaceChildren();
   for(const n of networks){const option=node('option',(n.locationName?n.locationName+' · ':'')+n.name);option.value=n.scope;this._selector.append(option);}
  }
  this._networks=networks;
  if(!networks.some(n=>n.scope===this._scope))this._changeScope(networks[0]?.scope);
  this._selector.value=this._scope||'';
  const network=this._network();
  this._selector.disabled=this._busy||!admin;
  this._refresh.disabled=this._busy||this._loading||!admin||!network;
  if(!admin||!network){
   this._generation++;this._loading=false;this._data=null;this._attempted=false;this._confirmation=null;this._content.replaceChildren();
   this._say(!admin?'admin':!network?'empty':'unavailable');return;
  }
  if(network.unavailable)this._say('unavailable');
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
 _tf(key,values){return this._t(key).replace(/\{(\w+)\}/g,(_,name)=>String(values[name]));}
 _say(key){this._message=key;this._status.textContent=key?this._t(key):'';if(key==='empty'){const link=node('a',this._language==='pt'?'Localizações e passos de ligação':'Locations and connection steps');link.href=this._config?.locations_path||'/config/integrations/integration/google_wifi_insights';this._status.append(document.createTextNode(' '),link);}}
 _changeScope(scope){if(this._batch)this._batch.stopRequested=true;this._batch=null;this._selectedNames.clear();this._scope=scope;this._generation++;this._data=null;this._loading=false;this._attempted=false;this._confirmation=null;this._content.replaceChildren();this._say(null);}
 async _call(service,data){const result=await this._hass.callWS({type:'call_service',domain:'google_wifi_insights',service,service_data:data,return_response:true});return result.response;}
 async _load(){
  const network=this._network();if(!this._admin||!network||this._busy)return;
  const request=++this._generation,scope=this._scope;this._attempted=true;this._loading=true;this._say('loading');this._refresh.disabled=true;
  try{const data=await this._call('get_management',{entity_id:network.entityId});
   if(request!==this._generation||!this._connected)return;
   if(data?.scope!==scope||!Array.isArray(data.points)||!Array.isArray(data.areas)||!Array.isArray(data.name_candidates))throw Error('Invalid management response');
   this._data=data;this._confirmation=null;this._say(this._network()?.unavailable?'unavailable':null);this._renderContent();
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
  const names=this._section('names','nameHint');
  this._nameConfirmHost=node('div');names.append(this._nameConfirmHost);
  if(this._data.rename?.writable){
   names.append(node('h3',this._t('manualNames')),node('p',this._t('manualHint')));
   names.append(node('p',this._tf('batchConcurrency',{limit:this._nameConcurrency()})));
   if(this._nameConcurrency()===1)names.append(node('p',this._t('batchUpgrade')));
   const toolbar=node('div');toolbar.className='buttons';toolbar.style.cssText='position:sticky;top:64px;z-index:1;padding:8px 0;background:var(--card-background-color)';
   const allLabel=node('label',this._t('selectAll'));allLabel.style.cssText='display:flex;align-items:center;gap:8px';
   this._selectAllNames=node('input');this._selectAllNames.type='checkbox';this._selectAllNames.setAttribute('aria-label',this._t('selectAll'));this._selectAllNames.style.cssText='width:20px;min-height:20px';
   this._selectAllNames.addEventListener('change',()=>{this._selectedNames.clear();if(this._selectAllNames.checked)for(const c of this._eligibleNames())this._selectedNames.set(c.entity_id,this._nameFingerprint(c));this._nameConfirmHost.replaceChildren();this._updateNameSelection();});allLabel.prepend(this._selectAllNames);
   this._renameSelected=button(this._t('renameSelected'),()=>this._confirmBatch(false));this._renameAll=button(this._t('renameAll'),()=>this._confirmBatch(true));
   toolbar.append(allLabel,this._renameSelected,this._renameAll);names.append(toolbar);
   this._selectionStatus=node('p');this._selectionStatus.setAttribute('role','status');this._selectionStatus.style.margin='0';toolbar.append(this._selectionStatus);
  }else{this._selectAllNames=this._renameSelected=this._renameAll=this._selectionStatus=null;}
  this._batchHost=node('div');names.append(this._batchHost);this._renderBatchProgress();
  names.append(node('h3',this._t('namesStatus')));const limit=node('p',this._t('nameLimit'));limit.className='notice';names.append(limit);
  this._nameStatus=node('p');this._nameStatus.setAttribute('role','status');names.append(this._nameStatus);
  this._nameToggle=button(this._t('enableNames'),()=>{
   const settings=this._network()?.nameSync||this._data.rename;
   if(settings?.enabled)this._nameRequest('set_name_sync',{entity_id:this._data.entity_id,enabled:false});
   else this._confirmName('enableNames',this._data.name,()=>this._nameRequest('set_name_sync',{entity_id:this._data.entity_id,enabled:true}));
  });this._nameToggle.dataset.write='name-toggle';this._nameToggle.dataset.entity=this._data.entity_id||'';names.append(this._nameToggle);
  this._nameResume=button(this._t('resumeNames'),()=>this._confirmName('resumeNames',this._data.name,()=>this._nameRequest('set_name_sync',{entity_id:this._data.entity_id,enabled:true})));this._nameResume.dataset.write='name';this._nameResume.dataset.entity=this._data.entity_id||'';names.append(this._nameResume);
  const guide=node('a',this._t('guide'));guide.href='https://support.google.com/googlehome/answer/6346150';guide.target='_blank';guide.rel='noopener noreferrer';names.append(guide);
  if(!this._data.name_candidates.length)names.append(node('p',this._t('noNames')));
  for(const candidate of this._data.name_candidates){
   const row=node('div');row.className='candidate';if(!this._data.rename?.writable)row.append(node('h3',candidate.proposed_name));row.append(node('p',this._t('google')+': '+candidate.google_name));
   if(this._data.rename?.excluded_station_ids?.includes(candidate.station_id))row.append(node('p',this._t('nameExcluded')));
   if(this._data.rename?.writable){
    const label=node('label',candidate.proposed_name);label.style.cssText='display:flex;align-items:center;gap:8px;font-weight:600;margin-bottom:12px';
    const check=node('input');check.type='checkbox';check.dataset.nameSelect=candidate.entity_id||'';check.setAttribute('aria-label',this._t('selectDevice')+' · '+candidate.proposed_name);check.style.cssText='width:20px;min-height:20px;margin:0';
    check.addEventListener('change',()=>{if(check.checked)this._selectedNames.set(candidate.entity_id,this._nameFingerprint(candidate));else this._selectedNames.delete(candidate.entity_id);this._nameConfirmHost.replaceChildren();this._updateNameSelection();});label.prepend(check);row.prepend(label);
   }
   const meta=node('p',candidate.mac_address);meta.className='meta';row.append(meta);const label=node('label',this._t('proposed')),input=node('input');input.readOnly=true;input.value=candidate.proposed_name;input.setAttribute('aria-label',this._t('selectName'));label.append(input);row.append(label,button(this._t('copy'),async()=>{
    try{await navigator.clipboard.writeText(candidate.proposed_name);this._say('copied');}catch{input.focus();input.select();this._say('copyFailed');}
   }));names.append(row);
   if(this._data.rename?.writable){
    const apply=button(this._t('applyName'),()=>this._confirmName('applyName',candidate.google_name+' → '+candidate.proposed_name,()=>this._nameRequest('rename_client',{entity_id:candidate.entity_id,expected_google_name:candidate.google_name,expected_mac:candidate.mac_address,expected_ha_name:candidate.proposed_name})));
    apply.dataset.write='name';apply.dataset.entity=candidate.entity_id||'';apply.dataset.expectedName=candidate.google_name;row.append(apply);
   }
  }
  const history=node('details');history.append(node('summary',this._t('recentNames')));names.append(history);
  const records=this._data.rename?.history||[],latestByClient=new Map(records.map(r=>[r.station_id,r.request_id]));
  for(const record of [...records].reverse()){
   const row=node('div');row.className='candidate';row.append(node('strong',record.old_name+' → '+(record.observed_name||record.new_name)),node('p',this._t(record.state)));
   const service=record.state==='unconfirmed'?'verify_name':record.state==='verified'&&record.kind==='rename'&&latestByClient.get(record.station_id)===record.request_id?'undo_name':null;
   if(service){const key=service==='undo_name'?'undoName':'verifyName',run=()=>this._nameRequest(service,{entity_id:this._data.entity_id,request_id:record.request_id});const b=button(this._t(key),()=>service==='undo_name'?this._confirmName(key,record.new_name+' → '+record.old_name,run):run());b.dataset.write='name';b.dataset.entity=this._data.entity_id||'';row.append(b);}
   history.append(row);
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
  this._refresh.disabled=Boolean(this._busy||this._loading||!this._admin||!network);this._selector.disabled=Boolean(this._busy||!this._admin);
  for(const b of this._content.querySelectorAll('button[data-write]')){
   const target=b.dataset.target===this._data?.network_id?network:network?.points.find(p=>p.id===b.dataset.target),operation=target?.operation;
   const pending=operation?.action===b.dataset.action&&['queued','sending','accepted','running'].includes(operation?.phase);
   const mayDisableNames=b.dataset.write==='name-toggle'&&(network?.nameSync||this._data?.rename)?.enabled;
   const changed=b.dataset.expectedName!==undefined&&this._hass?.states[b.dataset.entity]?.attributes?.google_name!==b.dataset.expectedName;
   b.disabled=Boolean((disabled&&!mayDisableNames)||this._busy||!this._admin||!b.dataset.entity||pending||changed);
  }
  for(const select of this._content.querySelectorAll('select'))select.disabled=Boolean(disabled);
  this._updateNameSelection();
 }
 _nameFingerprint(c){return JSON.stringify([c.station_id,c.entity_id,c.google_name,c.mac_address,c.proposed_name]);}
 _nameConcurrency(){const value=this._data?.rename?.max_concurrent;return Number.isInteger(value)&&value>0?Math.min(value,3):1;}
 _eligibleNames(){
  if(!this._data?.rename?.writable)return [];
  const pending=new Set((this._data.rename.history||[]).filter(r=>r.state==='unconfirmed').map(r=>r.station_id));
  return this._data.name_candidates.filter(c=>!pending.has(c.station_id)&&c.entity_id&&this._hass?.states[c.entity_id]?.state!=='unavailable'&&this._hass?.states[c.entity_id]?.attributes?.google_name===c.google_name);
 }
 _updateNameSelection(){
  const candidates=this._eligibleNames(),byId=new Map(candidates.map(c=>[c.entity_id,c]));
  for(const [id,fingerprint] of this._selectedNames)if(!byId.has(id)||this._nameFingerprint(byId.get(id))!==fingerprint)this._selectedNames.delete(id);
  const disabled=this._busy||this._loading||!this._admin||this._network()?.unavailable;
  for(const check of this._content.querySelectorAll('input[data-name-select]')){check.checked=this._selectedNames.has(check.dataset.nameSelect);check.disabled=Boolean(disabled||!byId.has(check.dataset.nameSelect));}
  if(!this._selectAllNames)return;
  const count=this._selectedNames.size;
  this._selectAllNames.checked=candidates.length>0&&count===candidates.length;this._selectAllNames.indeterminate=count>0&&count<candidates.length;this._selectAllNames.disabled=Boolean(disabled||!candidates.length);
  this._renameSelected.disabled=Boolean(disabled||!count);this._renameAll.disabled=Boolean(disabled||!candidates.length);
  this._selectionStatus.textContent=this._tf('selectionCount',{selected:count,eligible:candidates.length});
 }
 _confirmBatch(all){
  if(this._busy||!this._admin||this._network()?.unavailable)return;
  const preview=this._eligibleNames().filter(c=>all||this._selectedNames.has(c.entity_id)).map(c=>({station_id:c.station_id,entity_id:c.entity_id,google_name:c.google_name,mac_address:c.mac_address,proposed_name:c.proposed_name}));
  if(!preview.length)return;
  const scope=this._scope,generation=this._generation;
  this._confirmName(all?'renameAll':'renameSelected',preview.length===1?(this._language==='pt'?'1 dispositivo':'1 device'):this._tf('batchDevices',{count:preview.length}),()=>this._runNameBatch(preview,scope,generation),preview);
 }
 _confirmName(label,target,run,preview=[]){
  if(this._busy||!this._admin||this._network()?.unavailable)return;
  this._nameConfirmHost.replaceChildren();const box=node('div');box.className='confirmation';box.append(node('strong',this._t(label)+' · '+(target===this._data.name?'':target+' · ')+this._data.name),node('p',this._t(label==='undoName'?'nameUndoConfirm':'nameConfirm')));
  if(preview.length){box.append(node('p',this._tf('batchHint',{limit:this._nameConcurrency()})));const list=node('ul');list.style.cssText='max-height:220px;overflow:auto;padding-inline-start:24px';for(const c of preview)list.append(node('li',c.google_name+' → '+c.proposed_name+' · '+c.mac_address));box.append(list);}
  const confirm=button(this._t('confirm'),()=>{this._nameConfirmHost.replaceChildren();run();});confirm.className='primary';box.append(confirm,button(this._t('cancel'),()=>this._nameConfirmHost.replaceChildren()));this._nameConfirmHost.append(box);confirm.focus();
 }
 _renderBatchProgress(){
  if(!this._batchHost)return;this._batchHost.replaceChildren();const batch=this._batch;if(!batch||batch.scope!==this._scope)return;
  const box=node('div');box.className='notice';const done=batch.results.length,verified=batch.results.filter(r=>r.state==='verified').length,skipped=batch.results.filter(r=>r.state==='skipped').length;
  const active=batch.active.size,review=batch.results.filter(r=>!['verified','skipped'].includes(r.state)).length;
  const status=node('p',batch.running?(batch.stopRequested?this._tf('batchStopping',{active}):this._tf('batchWorking',{active,done,total:batch.total})):this._t(batch.stopped?'batchStopped':'batchComplete'));
  status.setAttribute('role','status');status.setAttribute('aria-live','polite');box.append(status,node('p',this._tf('batchSummary',{verified,skipped,active,review,remaining:batch.total-done-active})));
  for(const name of batch.active.values())box.append(node('p',name+' · '+this._t('sendingName')));
  if(batch.refreshFailed)box.append(node('p',this._t('batchRefreshFailed')));
  const progress=node('progress');progress.max=batch.total;progress.value=done;progress.setAttribute('aria-label',this._t('batchProgress'));progress.style.width='100%';box.append(progress);
  if(batch.results.length){const list=node('ul');list.style.cssText='max-height:220px;overflow:auto;padding-inline-start:24px';for(const r of [...batch.results].sort((a,b)=>a.index-b.index))list.append(node('li',r.name+' · '+this._t(r.state)));box.append(list);}
  if(batch.running){const stop=button(this._t('stopBatch'),()=>{batch.stopRequested=true;this._renderBatchProgress();});stop.disabled=batch.stopRequested;box.append(stop);}
  this._batchHost.append(box);
 }
 async _runNameBatch(preview,scope,generation){
  const sameView=()=>this._connected&&this._scope===scope&&this._generation===generation&&this._admin;
  const current=()=>sameView()&&Boolean(this._network())&&!this._network().unavailable;
  if(this._busy||!current())return;
  const batch={scope,total:preview.length,results:[],active:new Map(),limit:this._nameConcurrency(),running:true,stopRequested:false,stopped:false};this._batch=batch;this._busy=true;this._say(null);this._updateDisabled();
  const run=async(candidate,index)=>{
   batch.active.set(candidate.entity_id,candidate.proposed_name);this._renderBatchProgress();
   let result='unconfirmed';
   try{
    const data=await this._call('rename_client',{entity_id:candidate.entity_id,expected_google_name:candidate.google_name,expected_mac:candidate.mac_address,expected_ha_name:candidate.proposed_name});
    if(data?.scope!==scope||!Array.isArray(data.name_candidates))throw Error('Wrong network response');
    const record=data.name_result;
    const matching=record?.station_id===candidate.station_id&&record.mac_address===candidate.mac_address&&record.new_name===candidate.proposed_name&&record.kind==='rename'&&record.automatic===false;
    result=matching&&['verified','rejected','cancelled'].includes(record.state)?record.state:'unconfirmed';
   }catch{result='unconfirmed';}
   finally{
    batch.active.delete(candidate.entity_id);batch.results.push({index,name:candidate.proposed_name,state:result});
    if(sameView())this._selectedNames.delete(candidate.entity_id);
    if(result!=='verified'){batch.stopped=true;batch.stopRequested=true;}
    if(this._batch===batch&&sameView())this._renderBatchProgress();
   }
  };
  let index=0;
  try{
   while(index<preview.length&&!batch.stopRequested&&current()){
    const wave=[];
    while(index<preview.length&&wave.length<batch.limit&&!batch.stopRequested&&current()){
     const position=index++,candidate=preview[position],eligible=this._eligibleNames().find(c=>c.entity_id===candidate.entity_id);
     if(!eligible||this._nameFingerprint(eligible)!==this._nameFingerprint(candidate)){batch.results.push({index:position,name:candidate.proposed_name,state:'skipped'});this._selectedNames.delete(candidate.entity_id);continue;}
     wave.push(run(candidate,position));
    }
    this._renderBatchProgress();await Promise.allSettled(wave);
    // Concurrent service responses can arrive out of order. Refresh the cached
    // view once after the group drains instead of merging stale snapshots.
    if(sameView()){
     try{
      const data=await this._call('get_management',{entity_id:this._network().entityId});
      if(!sameView())break;
      if(data?.scope!==scope||!Array.isArray(data.name_candidates)||!Array.isArray(data.points)||!Array.isArray(data.areas))throw Error('Wrong management response');
      this._data=data;
     }catch{batch.refreshFailed=true;batch.stopped=true;batch.stopRequested=true;}
    }
   }
  }finally{
   batch.running=false;batch.stopped||=batch.results.length<batch.total;this._busy=false;
   if(sameView()){this._renderContent();this._updateDisabled();}else if(this._connected)this._update();
  }
 }
 async _nameRequest(service,payload){
  if(this._busy||!this._admin||this._network()?.unavailable&&!(service==='set_name_sync'&&!payload.enabled))return;
  const generation=this._generation,scope=this._scope;this._busy=true;this._say('sending');this._updateDisabled();
  try{const data=await this._call(service,payload);if(generation!==this._generation||!this._connected)return;if(data?.scope!==scope)throw Error('Wrong network');this._data=data;const state=data.name_result?.state;this._say(service==='set_name_sync'?(payload.enabled?'namesEnabled':'namesDisabled'):state==='verified'?'nameSaved':state==='rejected'?'nameRejected':'nameUnconfirmed');this._renderContent();}
  catch{if(generation===this._generation)this._say('actionFailed');}
  finally{this._busy=false;this._updateDisabled();}
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
  const names=network?.nameSync||this._data?.rename;
  if(this._nameStatus&&names){this._nameStatus.textContent=this._t('namesStatus')+': '+this._t(names.paused_reason?'paused':names.enabled?'enabled':'disabled')+' · '+this._t('renamedCount')+': '+(names.verified_count||0)+' · '+this._t('pendingCount')+': '+(names.unconfirmed_count||0)+'. '+this._t('refreshNames');this._nameToggle.textContent=this._t(names.enabled?'disableNames':'enableNames');this._nameResume.hidden=!names.paused_reason||!names.enabled;}
  for(const item of this._feedbackNodes||[]){
   const target=item.target.kind==='network'?network:network?.points.find(p=>p.id===item.target.id);
   const feedback=operationFeedback(target?.operation,this._language);
   item.node.textContent=feedback?this._t('latest')+': '+feedback.actionLabel+' · '+feedback.label+'\n'+feedback.note:'';
  }
 }
}
if(!customElements.get('google-wifi-management'))customElements.define('google-wifi-management',GwiManagement);
