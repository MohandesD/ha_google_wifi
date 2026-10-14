// Render only collected information. Provider text is escaped; no HTML is executed.
const WORDS={
 en:{firmware:'Firmware and updates',installed:'Installed firmware (Google)',localVersion:'Firmware reported locally',status:'Update status',channel:'Update channel',required:'Update required',offered:'Offered firmware',progress:'Update progress (reported)',rawScale:'The progress scale is not established; this is the raw value, not a percentage.',noneOffered:'No version offered',notes:'Firmware release notes',noNotes:'No release notes supplied.',historicalNotes:'Google returned historical notes; none matches the queried installed version.',matches:'Matches queried firmware',queried:'Queried version',readAt:'Retrieved',stale:'Older reading',noLan:'Local readings are unavailable. Configure a local-mode entry or a LAN gateway in integration options.',yes:'Yes',no:'No',unknown:'Not supplied',lan:'LAN information',wan:'WAN information',configuration:'Network configuration',cloud:'Google cloud',local:'Local point',host:'Point IP',mode:'IP configuration',ip:'IP address',gateway:'Gateway',netmask:'Netmask',prefix:'Prefix length',lease:'DHCP lease (seconds)',dns:'DNS mode',servers:'DNS servers',link:'Ethernet link',lanLink:'LAN port link',online:'Internet online',environment:'API environment',updateUrl:'Firmware update URL',dhcpStart:'DHCP pool start',dhcpEnd:'DHCP pool end',ipv6:'IPv6 enabled',upnp:'UPnP enabled',guest:'Guest Wi-Fi enabled',all:'All supplied information',endpoints:'Local endpoint availability',hardware:'Hardware setup information',emptyHardware:'No additional hardware information supplied.',idle:'Idle',checking:'Checking',downloading:'Downloading',updating:'Updating',available:'Available',not_supported:'Not supported',denied:'Access denied',unavailable:'Unavailable',not_configured:'Not configured'},
 pt:{firmware:'Firmware e atualizações',installed:'Firmware instalado (Google)',localVersion:'Firmware reportado localmente',status:'Estado da atualização',channel:'Canal de atualização',required:'Atualização necessária',offered:'Firmware disponibilizado',progress:'Progresso reportado',rawScale:'A escala do progresso não está confirmada; este é o valor original, sem conversão para percentagem.',noneOffered:'Nenhuma versão disponibilizada',notes:'Notas de firmware',noNotes:'Não foram fornecidas notas de firmware.',historicalNotes:'A Google devolveu notas históricas; nenhuma corresponde à versão instalada consultada.',matches:'Corresponde ao firmware consultado',queried:'Versão consultada',readAt:'Recolhido',stale:'Leitura antiga',noLan:'As leituras locais estão indisponíveis. Configura uma entrada local ou o gateway LAN nas opções da integração.',yes:'Sim',no:'Não',unknown:'Não fornecido',lan:'Informação LAN',wan:'Informação WAN',configuration:'Configuração da rede',cloud:'Google cloud',local:'Point local',host:'IP do point',mode:'Configuração IP',ip:'Endereço IP',gateway:'Gateway',netmask:'Máscara de rede',prefix:'Comprimento do prefixo',lease:'Concessão DHCP (segundos)',dns:'Modo DNS',servers:'Servidores DNS',link:'Ligação Ethernet',lanLink:'Ligação da porta LAN',online:'Internet ligada',environment:'Ambiente da API',updateUrl:'URL de atualização do firmware',dhcpStart:'Início da gama DHCP',dhcpEnd:'Fim da gama DHCP',ipv6:'IPv6 ativo',upnp:'UPnP ativo',guest:'Wi-Fi de convidados ativo',all:'Toda a informação fornecida',endpoints:'Disponibilidade dos endpoints locais',hardware:'Informação adicional de hardware',emptyHardware:'Não foi fornecida informação adicional de hardware.',idle:'Em espera',checking:'A verificar',downloading:'A descarregar',updating:'A atualizar',available:'Disponível',not_supported:'Não suportado',denied:'Acesso recusado',unavailable:'Indisponível',not_configured:'Não configurado'}
};
const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text=(key,lang)=>WORDS[lang==='pt'?'pt':'en'][key]||key;
const value=(v,lang)=>v===true?text('yes',lang):v===false?text('no',lang):v==null||v===''?text('unknown',lang):Array.isArray(v)?v.map(x=>value(x,lang)).join(', '):typeof v==='object'?JSON.stringify(v):String(v);
const pairs=(rows,lang)=>`<dl class="gwi-info-pairs">${rows.map(([label,v])=>`<dt>${escape(text(label,lang))}</dt><dd>${escape(value(v,lang))}</dd>`).join('')}</dl>`;
export function informationSummary(label,language='en'){
 const pt=language==='pt';
 return `<summary class="gwi-disclosure-summary"><svg class="gwi-disclosure-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg><span class="gwi-disclosure-label">${escape(label)}</span><span class="gwi-disclosure-action" aria-hidden="true"><span class="gwi-expand">${pt?'Expandir':'Expand'}</span><span class="gwi-collapse">${pt?'Recolher':'Collapse'}</span></span></summary>`;
}
const raw=(data,lang,key)=>`<details data-gwi-disclosure="${key}" class="gwi-info-raw">${informationSummary(text('all',lang),lang)}<pre tabindex="0" role="region" aria-label="${escape(text('all',lang))}" data-gwi-scroll="${key}">${escape(JSON.stringify(data||{},null,2))}</pre></details>`;
export const informationCss=`
.gwi-disclosure-summary{box-sizing:border-box;list-style:none;cursor:pointer;min-height:48px;display:flex;align-items:center;gap:10px;padding:10px 12px!important;border:1px solid var(--divider-color,#d7dce3);border-radius:8px;background:var(--secondary-background-color,#f4f6fa);color:var(--primary-text-color,#172033)!important;font-size:13px;font-weight:600;user-select:none}
.gwi-disclosure-summary::-webkit-details-marker{display:none}
.gwi-disclosure-summary:hover{border-color:var(--primary-color,#3367d6)}
.gwi-disclosure-summary:focus-visible,.gwi-information pre:focus-visible{outline:3px solid var(--primary-color,#3367d6);outline-offset:3px}
.gwi-disclosure-chevron{flex:0 0 20px;width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2}
details[open]>.gwi-disclosure-summary>.gwi-disclosure-chevron{transform:rotate(90deg)}
.gwi-disclosure-label{flex:1;min-width:0;overflow-wrap:anywhere}
.gwi-disclosure-action{flex-shrink:0;font-size:12px;color:var(--primary-color,#3367d6);font-weight:500}
.gwi-disclosure-summary .gwi-collapse{display:none}
details[open]>.gwi-disclosure-summary .gwi-expand{display:none}
details[open]>.gwi-disclosure-summary .gwi-collapse{display:inline}
.gwi-information details{margin:10px 0}
.gwi-information pre{overscroll-behavior:contain;scrollbar-gutter:stable}
.gwi-information{color:var(--primary-text-color,#172033);font-size:13px;line-height:1.55;min-width:0}.gwi-information h3{font-size:16px;margin:16px 0 10px}.gwi-information h4{font-size:14px;margin:12px 0 6px}.gwi-info-pairs{display:grid;grid-template-columns:minmax(110px,1fr) minmax(0,1.5fr);gap:6px 14px;margin:8px 0 14px}.gwi-info-pairs dt{color:var(--secondary-text-color,#5e6878)}.gwi-info-pairs dd{margin:0;overflow-wrap:anywhere;white-space:pre-line}.gwi-info-note{font-size:12px;color:var(--secondary-text-color,#5e6878);margin:8px 0;white-space:pre-line}.gwi-info-warning{border-left:3px solid var(--warning-color,#b36a05);padding-left:10px}.gwi-info-raw{margin:12px 0}.gwi-information summary{cursor:pointer;min-height:44px;display:flex;align-items:center;gap:8px}.gwi-information summary:focus-visible{outline:3px solid var(--primary-color,#3367d6);outline-offset:3px}.gwi-information pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;background:var(--secondary-background-color,#f4f6fa);padding:12px;border-radius:10px;max-height:420px;overflow:auto}.gwi-info-version{font-size:12px;font-weight:600}.gwi-info-release{border-top:1px solid var(--divider-color,#e5e8ed);padding:10px 0}.gwi-info-release p{white-space:pre-line;overflow-wrap:anywhere}.gwi-info-summary{font-size:11px;line-height:1.5;color:var(--secondary-text-color,#5e6878);overflow-wrap:anywhere}.gwi-info-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr));gap:18px}.gwi-info-stamp{font-size:11px;color:var(--secondary-text-color,#5e6878)}@media(max-width:460px){.gwi-info-pairs{grid-template-columns:minmax(95px,1fr) minmax(0,1.3fr);gap:6px 8px}}`;
function stamp(info,lang,when){const at=info?.retrieved_at||info?.lan_retrieved_at;return `${info?.stale||info?.lan_stale?text('stale',lang)+' · ':''}${at?text('readAt',lang)+' · '+when(at):''}`;}
export function firmwareSummary(point,language='en'){
 const f=point.firmwareInfo||point.firmware_information||{};
 return [f.installed_version||f.local_version,f.update_status?text(f.update_status,language):null].filter(Boolean).map(escape).join(' · ');
}
export function pointInformation(point,language='en',when=v=>v){
 const f=point.firmwareInfo||point.firmware_information||{},lan=point.lanInfo||point.lan_information||{},notes=f.release_notes||{},local=lan.status||{},wan=local.wan||{},system=local.system||{},dns=local.dns||{};
 const hardware=point.hardwareInfo||point.hardware_setup_information||{};
 const fresh=!!local.software&&!lan.stale;
 const noteRows=Array.isArray(notes.notes)?notes.notes:[];
 const installed=f.installed_version||f.local_version;
 const body=`<h3>${escape(text('firmware',language))}</h3>${pairs([['installed',installed],['localVersion',f.local_version],['status',f.update_status?text(f.update_status,language):null],['channel',f.update_channel],['required',f.update_required],['offered',f.reported_new_version==='0.0.0.0'?text('noneOffered',language):f.reported_new_version],['progress',f.update_progress_raw]],language)}<p class="gwi-info-note">${escape(text('rawScale',language))}</p><p class="gwi-info-stamp">${escape(stamp(f,language,when))}</p><details data-gwi-disclosure="notes">${informationSummary(text('notes',language)+' · '+noteRows.length,language)}<p class="gwi-info-stamp">${escape(text('queried',language))} · ${escape(notes.queried_version||text('unknown',language))}<br>${escape(stamp(notes,language,when))}</p>${noteRows.length&&!notes.matching_installed?`<p class="gwi-info-note gwi-info-warning">${escape(text('historicalNotes',language))}</p>`:''}${noteRows.length?noteRows.map(n=>`<article class="gwi-info-release"><span class="gwi-info-version">${escape(n.version)}${n.matches_installed?' · '+escape(text('matches',language)):''}</span><h4>${escape(n.title)}</h4><p>${escape(n.description)}</p></article>`).join(''):`<p>${escape(text('noNotes',language))}</p>`}</details><h3>${escape(text('lan',language))}</h3>${!fresh?`<p class="gwi-info-note gwi-info-warning">${escape(text('noLan',language))}</p>`:pairs([['host',lan.host],['mode',wan.ipMethod],['ip',wan.localIpAddress],['gateway',wan.gatewayIpAddress],['prefix',wan.ipPrefixLength],['lease',wan.leaseDurationSeconds],['online',wan.online],['link',wan.ethernetLink],['lanLink',system.lan0Link],['dns',dns.mode],['servers',dns.servers],['environment',lan.developer_configuration?.apiEnvironment],['updateUrl',lan.developer_configuration?.autoUpdateUrl]],language)}<p class="gwi-info-stamp">${escape(stamp(lan,language,when))}</p><details data-gwi-disclosure="endpoints">${informationSummary(text('endpoints',language),language)}${pairs(Object.entries(lan.endpoints||{}).map(([name,s])=>[name,text(s.state||'unavailable',language)+(s.http_status?' · HTTP '+s.http_status:'')+(s.stale?' · '+text('stale',language):'')]),language)}</details>${raw({firmware:f,lan,hardware_setup:hardware},language,'point-all')}`;
 return `<style>${informationCss}</style><section class="gwi-information">${body}</section>`;
}
export function networkInformation(network,language='en',when=v=>v){
 const info=network.networkInfo||network.network_information||{},cloud=info.cloud||{},wan=cloud.wan_properties||{},lan=cloud.lan_settings||{},ws=cloud.wan_settings||{};
 return `<style>${informationCss}</style><section class="gwi-information"><h3>${escape(text('configuration',language))}</h3><p class="gwi-info-stamp">${escape(text('cloud',language))} · ${escape(stamp(info,language,when))}</p><div class="gwi-info-grid"><div><h4>${escape(text('wan',language))}</h4>${pairs([['mode',wan.wanMode],['ip',wan.ipAddress],['gateway',wan.gateway],['netmask',wan.ipNetmask],['servers',wan.dnsServers],['dns',ws.dnsConfig?.dnsMode],['ipv6',ws.ipv6Enabled]],language)}</div><div><h4>${escape(text('lan',language))}</h4>${pairs([['ip',lan.ipAddress],['netmask',lan.netmask],['dhcpStart',lan.dhcpPoolBegin],['dhcpEnd',lan.dhcpPoolEnd],['upnp',lan.upnpEnabled],['guest',cloud.guest_wifi?.enabled]],language)}</div></div>${raw(info,language,'network-all')}</section>`;
}

// Patch collected information in place. Native details own their open state;
// live telemetry must not replace the controls or reset a JSON scroll region.
const informationMarkup=new WeakMap();
const nodeKey=node=>node.nodeType===1?(node.getAttribute('data-gwi-key')||node.getAttribute('data-gwi-disclosure')||node.getAttribute('data-gwi-scroll')):null;
const sameNode=(node,next)=>node?.nodeType===next.nodeType&&node.nodeName===next.nodeName&&nodeKey(node)===nodeKey(next);
function patchInformation(parent,source){
 const remaining=new Set(parent.childNodes);
 let cursor=parent.firstChild;
 for(const next of source.childNodes){
  const key=nodeKey(next);
  let node=sameNode(cursor,next)?cursor:[...remaining].find(old=>sameNode(old,next)&&(key||!nodeKey(old)));
  if(!node){node=next.cloneNode(true);parent.insertBefore(node,cursor);}
  else{
   remaining.delete(node);
   if(node!==cursor)parent.insertBefore(node,cursor);
   if(node.nodeType===1){
    for(const attr of [...node.attributes])if(!(node.localName==='details'&&attr.name==='open')&&!next.hasAttribute(attr.name))node.removeAttribute(attr.name);
    for(const attr of next.attributes)if(!(node.localName==='details'&&attr.name==='open')&&node.getAttribute(attr.name)!==attr.value)node.setAttribute(attr.name,attr.value);
    patchInformation(node,next);
   }else if(node.nodeValue!==next.nodeValue)node.nodeValue=next.nodeValue;
  }
  cursor=node.nextSibling;
 }
 for(const node of remaining)node.remove();
}
export function renderInformation(host,markup,scope=''){
 const previous=informationMarkup.get(host);
 if(previous?.markup===markup&&previous.scope===scope)return;
 if(previous&&previous.scope!==scope)host.replaceChildren();
 const scroll=[...host.querySelectorAll('pre')].map(node=>({node,top:node.scrollTop,left:node.scrollLeft}));
 const template=host.ownerDocument.createElement('template');template.innerHTML=markup;
 patchInformation(host,template.content);
 for(const {node,top,left} of scroll)if(host.contains(node)){node.scrollTop=top;node.scrollLeft=left;}
 informationMarkup.set(host,{markup,scope});
}
export function informationPanelAfter(target){
 if(!target)return null;
 let panel=target.nextElementSibling;
 if(!panel?.hasAttribute('data-gwi-information-panels')){
  panel=target.ownerDocument.createElement('section');
  panel.setAttribute('data-gwi-information-panels','');panel.className='network-bottom';
  target.after(panel);
 }
 return panel;
}
