// Read only observed HA entities. Never infer a point or mesh link from a name/IP.
const TEXT = {
  en: {
    action_queued:"Queued",action_sending:"Sending request",action_accepted:"Request accepted",action_running:"Running",action_completed:"Completed",action_failed:"Failed",action_cancelled:"Cancelled",action_unconfirmed:"Status not confirmed",
    action_restart_network:"Restart network",action_restart_point:"Restart point",action_test_internet:"Internet speed test",action_test_mesh:"Mesh speed test",action_test_local:"Local speed test",action_test_clients:"Client WiFi speed test",
    action_mesh_preparing_note:"Preparing the measurement server on the primary point. The mesh measurement has not finished.",action_mesh_measuring_note:"Testing the selected point against the primary. Metrics are refreshed after the test finishes.",
    action_google_note:"Status reported by Google. A restarting point may still be reconnecting; test results can take longer to appear.",action_unconfirmed_note:"Google has not confirmed completion. Check the point before sending the request again.",action_timeout_note:"No completion was confirmed within ten minutes. Monitoring stopped without repeating the request.",action_failed_note:"Google rejected or failed the operation. Check the action status for details.",action_auth_note:"Renew Google authentication to check the operation status.",action_rate_note:"Google requested a pause. The write is not retried automatically.",action_status_missing_note:"Google's status lookup is unavailable; the last confirmed state is shown.",
    back_overview:"Back to overview",navigation_config_error:"overview_path must be a local Home Assistant path.",
    wifi_test:"Stored WiFi test · {speed} Mbit/s · {point} · {time}",usage_24h:"Usage 24h · ↓ {download} · ↑ {upload}",controls:"Google controls",history:"Usage history",backhaul:"Backhaul · {type}",mesh_test:"Stored mesh test · {speed} Mbit/s · {time}",capabilities:"Google capabilities",operation:"Last operation · {state}",
    title:"WiFi network map",subtitle:"Devices by point and connection quality",
    unavailable:"Unavailable",unknown_point:"unknown",unknown_status:"Unknown status",
    wired:"Wired",wired_no_rssi:"Wired · no RSSI",no_measurement:"No measurement",no_rating:"No rating",
    excellent:"Excellent",good:"Good",fair:"Fair",weak:"Weak",good_legend:"Good / excellent",
    client_details:"{name}. {quality}. Point {point}. View details.",
    traffic:"↓ {download} · ↑ {upload} Mbit/s",user_name:"Custom name",no_traffic:"No traffic measurement",
    primary:"Primary point",mesh_quality:"To primary · {quality}",no_clients_data:"Clients · no data",
    observed_clients_one:"{count} observed client",observed_clients_other:"{count} observed clients",
    connected_clients_one:"{count} connected client observed",connected_clients_other:"{count} connected clients observed",
    rated:"{count} with quality",coverage:"{count}/{total} with quality",
    weak_clients_one:"{count} weak connection observed",weak_clients_other:"{count} weak connections observed",
    mesh_title:"Google mesh assessments",mesh_description:"These ratings compare each point with the primary. Points can communicate with other points in range, but Google does not report their radio paths or pairwise measurements.",
    compared_with:"Compared with {name} · {quality}",peer_links:"Connections between other points",peer_unknown:"Not reported by Google",
    real_rssi:"{count} with measured RSSI",rssi_shelly:"RSSI measured by Shelly",google_quality:"Google quality · {quality}",roaming:"Roaming controls",metrics:"Google metrics",radio_details:"Channel {channel} · {bssid}",wan_test:"Last Internet test · ↓ {download} · ↑ {upload} Mbit/s · {time}",roaming_hint:"Below the signal threshold, Shelly looks for a better access point at the chosen interval. It decides whether to move; a move is not guaranteed. Interval 0 disables roaming.",
    no_root:"Google has not identified the primary point for this network yet.",
    mesh_details:"{name}. Quality to {primary}: {quality}. View details.",
    offline_no_rating:"Offline · no rating",no_satellites:"No other points associated with the primary.",
    no_entities:"No Google WiFi Insights entities yet. Set up the integration to populate the map.",
    query_unavailable:"Network query unavailable",local_mode:"Local mode · clients and signal not provided",
    client_groups:"Devices connected to each point",collapse:"Collapse devices",
    more_one:"Show {count} more device",more_other:"Show {count} more devices",
    local_associations:"Client associations require validation with the Google account",no_observation:"No current observation",
    no_associations:"No clients with a confirmed association",unassigned:"Point not identified",
    limits:"RSSI in dBm is measured by the device radio; Google ratings are shown separately. Google does not report channel utilization, retries or radio paths between points, so these measurements do not establish saturation. Grey indicates missing data.",
    config_error:"Use a text title and max_clients between 1 and 100.",
    card_description:"Points, associated clients and observed connection quality",
  },
  pt: {
    action_mesh_preparing_note:"A preparar o servidor de medição no point principal. A medição mesh ainda não terminou.",action_mesh_measuring_note:"A testar o point selecionado com o principal. As métricas são atualizadas quando o teste termina.",
    action_queued:"Em fila",action_sending:"A enviar pedido",action_accepted:"Pedido aceite",action_running:"Em execução",action_completed:"Concluído",action_failed:"Falhou",action_cancelled:"Cancelado",action_unconfirmed:"Estado não confirmado",
    action_restart_network:"Reiniciar rede",action_restart_point:"Reiniciar point",action_test_internet:"Teste de velocidade da Internet",action_test_mesh:"Teste de velocidade mesh",action_test_local:"Teste de velocidade local",action_test_clients:"Teste de velocidade WiFi dos dispositivos",
    action_google_note:"Estado comunicado pela Google. Um point a reiniciar pode ainda estar a restabelecer a ligação; os resultados dos testes podem demorar a aparecer.",action_unconfirmed_note:"A Google ainda não confirmou a conclusão. Verifica o point antes de voltar a enviar o pedido.",action_timeout_note:"A conclusão não foi confirmada em dez minutos. A monitorização terminou sem repetir o pedido.",action_failed_note:"A Google rejeitou o pedido ou a operação falhou. Consulta o estado da ação para mais detalhes.",action_auth_note:"Renova a autenticação Google para consultar o estado da operação.",action_rate_note:"A Google pediu uma pausa. O comando não é repetido automaticamente.",action_status_missing_note:"A consulta do estado à Google está indisponível; é mostrado o último estado confirmado.",
    back_overview:"Voltar à visão geral",navigation_config_error:"overview_path deve ser um caminho local do Home Assistant.",
    wifi_test:"Teste WiFi guardado · {speed} Mbit/s · {point} · {time}",usage_24h:"Utilização 24h · ↓ {download} · ↑ {upload}",controls:"Controlos Google",history:"Histórico de utilização",backhaul:"Backhaul · {type}",mesh_test:"Teste mesh guardado · {speed} Mbit/s · {time}",capabilities:"Capacidades Google",operation:"Última operação · {state}",
    title:"Mapa da rede WiFi",subtitle:"Dispositivos por ponto e qualidade das ligações",
    unavailable:"Indisponível",unknown_point:"desconhecido",unknown_status:"Estado desconhecido",
    wired:"Cabo",wired_no_rssi:"Cabo · sem RSSI",no_measurement:"Sem medição",no_rating:"Sem classificação",
    excellent:"Excelente",good:"Boa",fair:"Razoável",weak:"Fraca",good_legend:"Boa / excelente",
    client_details:"{name}. {quality}. Ponto {point}. Ver detalhes.",
    traffic:"↓ {download} · ↑ {upload} Mbit/s",user_name:"Nome personalizado",no_traffic:"Sem medição de tráfego",
    primary:"Ponto principal",mesh_quality:"Até ao principal · {quality}",no_clients_data:"Clientes · sem dados",
    observed_clients_one:"{count} cliente observado",observed_clients_other:"{count} clientes observados",
    connected_clients_one:"{count} cliente ligado observado",connected_clients_other:"{count} clientes ligados observados",
    rated:"{count} com qualidade",coverage:"{count}/{total} com qualidade",
    weak_clients_one:"{count} ligação fraca observada",weak_clients_other:"{count} ligações fracas observadas",
    mesh_title:"Avaliações Google da malha",mesh_description:"Estas classificações comparam cada ponto com o principal. Os pontos podem comunicar com outros pontos ao alcance, mas a Google não disponibiliza os percursos rádio nem medições de cada par.",
    compared_with:"Comparado com {name} · {quality}",peer_links:"Ligações entre os outros pontos",peer_unknown:"Não disponibilizado pela Google",
    real_rssi:"{count} com RSSI medido",rssi_shelly:"RSSI medido pelo Shelly",google_quality:"Qualidade Google · {quality}",roaming:"Controlos de roaming",metrics:"Métricas Google",radio_details:"Canal {channel} · {bssid}",wan_test:"Último teste da Internet · ↓ {download} · ↑ {upload} Mbit/s · {time}",roaming_hint:"Abaixo do limite de sinal, o Shelly procura um ponto com melhor sinal no intervalo escolhido. É o Shelly que decide a troca; esta não é garantida. O intervalo 0 desativa o roaming.",
    no_root:"O Google ainda não identificou o ponto principal desta rede.",
    mesh_details:"{name}. Qualidade até {primary}: {quality}. Ver detalhes.",
    offline_no_rating:"Offline · sem classificação",no_satellites:"Sem outros pontos associados ao principal.",
    no_entities:"Ainda não há entidades Google WiFi Insights. Configure a integração para preencher o mapa.",
    query_unavailable:"Consulta indisponível",local_mode:"Modo local · clientes e sinal não disponibilizados",
    client_groups:"Dispositivos ligados a cada ponto",collapse:"Recolher dispositivos",
    more_one:"Ver mais {count} dispositivo",more_other:"Ver mais {count} dispositivos",
    local_associations:"Associações de clientes por validar com a conta Google",no_observation:"Sem observação atual",
    no_associations:"Sem clientes com associação confirmada",unassigned:"Ponto por identificar",
    limits:"O RSSI em dBm é medido pelo rádio do dispositivo; as classificações Google aparecem separadas. A Google não disponibiliza ocupação do canal, retransmissões nem percursos entre pontos, pelo que estas medições não demonstram saturação. Cinzento indica dados em falta.",
    config_error:"Use um título de texto e max_clients entre 1 e 100.",
    card_description:"Pontos, clientes associados e qualidade de ligação observada",
  },
};

export function languageOf(value) {
  const raw = typeof value === "string" ? value : value?.language || value?.locale?.language;
  const code = typeof raw === "string" ? raw.replaceAll("_","-").toLowerCase() : "en";
  return code.split("-")[0] === "pt" ? "pt" : "en";
}

export function isLocalHaPath(value) {
  return typeof value === "string" && /^\/(?!\/)[^\\?#\x00-\x20]*$/.test(value);
}

export function overviewPath(config = {}, pathname = "") {
  if (config.overview_path != null) return isLocalHaPath(config.overview_path) ? config.overview_path : null;
  if (!isLocalHaPath(pathname) || !/\/(?:mapa|map|diagnostics)\/?$/.test(pathname)) return null;
  return pathname.replace(/\/(?:mapa|map|diagnostics)\/?$/, "/overview");
}

export function operationFeedback(operation, language="en") {
  if (!operation || !operation.phase || operation.phase === "none") return null;
  const t=translate(language),phase=["queued","sending","accepted","running","completed","failed","cancelled","unconfirmed"].includes(operation.phase)?operation.phase:"unconfirmed";
  const busy=["queued","sending","accepted","running"].includes(phase);
  const stageNote=busy&&operation.action==="test_mesh"?{preparing_server:"action_mesh_preparing_note",measuring:"action_mesh_measuring_note"}[operation.stage]:null;
  const note={monitoring_timeout:"action_timeout_note",authentication_required:"action_auth_note",rate_limited:"action_rate_note",status_unavailable:"action_status_missing_note"}[operation.status_error] || stageNote || (phase==="unconfirmed"?"action_unconfirmed_note":phase==="failed"?"action_failed_note":"action_google_note");
  return {phase,label:t("action_"+phase),actionLabel:t("action_"+operation.action),busy:["queued","sending","accepted","running"].includes(phase),
    symbol:{completed:"✓",failed:"!",cancelled:"−",unconfirmed:"?"}[phase]||"◌",note:t(note),at:operation.finished_at||operation.updated_at||operation.requested_at};
}

export function translate(language="en") {
  const selected=languageOf(language);
  const format=new Intl.NumberFormat(selected);
  const t=(key,values={})=>{
    const variant=typeof values.count==="number"?key+(values.count===1?"_one":"_other"):key;
    const text=TEXT[selected][variant] || TEXT[selected][key] || TEXT.en[variant] || TEXT.en[key] || key;
    return text.replace(/\{(\w+)\}/g,(_,name)=>typeof values[name]==="number"?format.format(values[name]):String(values[name]??""));
  };
  t.language=selected; t.number=value=>format.format(value);
  return t;
}

export function signal(value, unavailable = false, wired = false, language="en") {
  const t=translate(language);
  if (unavailable) return { key: "unknown", label: t("unavailable"), bars: 0 };
  if (wired) return { key: "unknown", label: t("wired_no_rssi"), bars: 0 };
  if (value === null || value === undefined || typeof value === "boolean" || value === "")
    return { key: "unknown", label: t("no_measurement"), bars: 0 };
  const rssi = Number(value);
  if (!Number.isFinite(rssi) || rssi < -110 || rssi >= 0)
    return { key: "unknown", label: t("no_measurement"), bars: 0 };
  const key = rssi >= -55 ? "excellent" : rssi >= -67 ? "good" : rssi >= -75 ? "fair" : "weak";
  return { key, label: `${t(key)} · ${t.number(rssi)} dBm`, bars: { excellent: 4, good: 3, fair: 2, weak: 1 }[key], rssi, source: "rssi" };
}

export function quality(category, source, unavailable = false, language="en") {
  const t=translate(language);
  if(unavailable || !["excellent","good","fair","weak"].includes(category) || !["google_connection_rating","google_mesh_rating"].includes(source))
    return { key:"unknown",label:t(unavailable?"unavailable":"no_rating"),bars:0 };
  return { key:category,label:t(category)+" · Google",bars:{excellent:4,good:3,fair:2,weak:1}[category],source };
}

function connection(a,language) {
  const t=translate(language);
  const wired=["WIRED","ETHERNET","CONNECTION_TYPE_WIRED"].includes(a.connection_type);
  const rating=quality(a.signal_quality,a.quality_source,false,language);
  const measured=signal(a.rssi,false,false,language);
  if(a.rssi_source==="shelly_wifi_status" && measured.key!=="unknown")return {...measured,measuredBy:"Shelly"};
  if(wired) return { ...rating,label:rating.key==="unknown"?t("wired"):`${t("wired")} · ${rating.label}`,bars:0,wired:true };
  return measured.key!=="unknown"?measured:rating;
}

export function mapModel(states, config = {}, language="en") {
  const t=translate(language),locale=t.language;
  const networks = new Map();
  const entries = Object.entries(states || {});
  const scopeOf = a => a.gwi_scope || a.gwi_network_id || "legacy";
  const selected = config.network_entity ? scopeOf(states?.[config.network_entity]?.attributes || {}) : null;
  const network = a => {
    const scope = scopeOf(a);
    if (selected && scope !== selected) return null;
    if (!networks.has(scope)) networks.set(scope, { scope, name: "Google WiFi", source: a.data_source, points: [], clients: [], unassigned: [] });
    return networks.get(scope);
  };
  for (const [entityId, state] of entries) {
    const a = state.attributes || {};
    if (a.gwi_kind === "network" && a.gwi_metric === "diagnosis") {
      const n = network(a);
      if (n) { n.entityId=entityId;n.name = a.device_name || "Google WiFi"; n.source = a.data_source; n.unavailable = state.state === "unavailable"; }
    }
  }
  for (const [entityId, state] of entries) {
    const a = state.attributes || {};
    if (a.gwi_kind === "point" && a.gwi_metric === "clients") {
      const n = network(a);
      if (!n) continue;
      const unavailable = state.state === "unavailable";
      n.points.push({
        id: a.gwi_item_id || entityId, entityId, name: a.device_name || entityId,
        online: unavailable ? null : typeof a.online === "boolean" ? a.online : null,
        unavailable, clients: [], count: ["unknown", "unavailable"].includes(state.state) ? null : Number.isFinite(Number(state.state)) ? Number(state.state) : null,
        isRoot: a.is_root === true, rootId: a.root_ap_id || null,
        area:unavailable?null:a.mapped_area,areaId:unavailable?null:a.mapped_area_id,
        mesh: quality(a.mesh_quality,a.mesh_quality_source,unavailable || a.online !== true,locale),
      });
    }
  }
  for (const [entityId, state] of entries) {
    const a = state.attributes || {};
    if (a.gwi_kind !== "client" || a.gwi_metric !== "point" || a.connected !== true) continue;
    const n = network(a);
    if (!n || state.state === "unavailable") continue;
    const client = {
      entityId, id: a.gwi_item_id || entityId, name: a.device_name || entityId,
      pointId: a.ap_id || null, pointName: a.point || null,
      associatedArea:a.associated_area || null,associatedAreaId:a.associated_area_id || null,
      signal: connection(a,locale),
      band: Object.hasOwn({BAND_2400_MHZ:2.4,BAND_5000_MHZ:5,BAND_6000_MHZ:6},a.wireless_band)?t.number({BAND_2400_MHZ:2.4,BAND_5000_MHZ:5,BAND_6000_MHZ:6}[a.wireless_band])+" GHz":null,
      download: a.download_mbps, upload: a.upload_mbps,
      ip:a.ip_address || null,mac:a.mac_address || null,nameSource:a.name_source,
      matchedDeviceId:a.ha_device_id || null,googleName:a.google_name || null,
      ownDeviceId:a.gwi_device_id || null,roaming:a.roaming_supported===true && a.radio_available===true,
      rssiSource:a.rssi_source || null,rssiObservedAt:a.rssi_observed_at || null,
      channel:a.wifi_channel,bssid:a.wifi_bssid,
      googleQuality:quality(a.signal_quality,a.quality_source,false,locale),
      wifiTest:a.wifi_test_mbps,wifiTestAt:a.wifi_test_at,wifiTestPoint:a.wifi_test_point,
      usageWindows:a.usage_windows || {},
      paused:a.internet_paused,priorityUntil:a.priority_until,controls:[],
    };
    n.clients.push(client);
    // Match the explicit AP ID within the same config entry/network only.
    const p = client.pointId ? n.points.find(p => p.id === client.pointId) : null;
    if (p) p.clients.push(client);
    else n.unassigned.push(client);
  }
  const rank={weak:0,fair:1,unknown:2,good:3,excellent:4};
  for(const [entityId,state] of entries) {
    const a=state.attributes || {},n=networks.get(scopeOf(a));
    if(!n)continue;
    if(a.gwi_kind==="network") {
      if(a.gwi_metric==="google_telemetry_at") {
        n.metricsEntityId=entityId;n.usageWindows=a.google_telemetry?.usage_windows || {};n.usageHourly=a.google_telemetry?.usage_hourly || [];
        n.networkInfo=a.google_telemetry?.networkInformation;
      }
      if(a.gwi_metric==="network_information_status")n.networkInfo=a.network_information;
      if(a.gwi_metric==="capability_count") {n.capabilities=a.capabilities;n.capabilitiesEntityId=entityId;}
      if(a.gwi_metric==="last_operation") {n.lastOperation=state.state;n.operationEntityId=entityId;}
      if(["wan_test_download_mbps","wan_test_upload_mbps","wan_test_at"].includes(a.gwi_metric))n[a.gwi_metric]=["unknown","unavailable"].includes(state.state)?null:state.state;
    }
    if(a.gwi_kind==="client" && a.gwi_metric==="google_telemetry_at") {
      const c=n.clients.find(c=>c.id===a.gwi_item_id);if(c)c.metricsEntityId=entityId;
    }
    if(a.gwi_kind==="point" && a.gwi_metric==="google_telemetry_at") {
      const p=n.points.find(p=>p.id===a.gwi_item_id);if(p){p.metricsEntityId=entityId;p.meshTest=a.mesh_test_mbps;p.meshTestAt=a.mesh_test_at;p.backhaul=a.backhaul_type;p.firmwareInfo=a.google_telemetry?.firmwareInformation;p.lanInfo=a.google_telemetry?.lanInformation;p.hardwareInfo=a.google_telemetry?.hardwareSetupInformation;}
    }
    if(a.gwi_kind==="point"){
      const p=n.points.find(p=>p.id===a.gwi_item_id);
      if(p){if(a.firmware_information)p.firmwareInfo=a.firmware_information;if(a.lan_information)p.lanInfo=a.lan_information;}
    }
    if(a.gwi_metric==="operation_status") {
      const target=a.gwi_kind==="network"?n:n.points.find(p=>p.id===a.gwi_item_id);
      if(target){target.operation=a.operation_feedback;target.operationStatusEntityId=entityId;}
    }
    if(/^(button|switch|number)\./.test(entityId) && !["roam_rssi_threshold","roam_interval","roaming_enabled"].includes(a.gwi_metric)) {
      const target=a.gwi_kind==="network"?n:a.gwi_kind==="point"?n.points.find(p=>p.id===a.gwi_item_id):n.clients.find(c=>c.id===a.gwi_item_id);
      if(target)(target.controls ||= []).push({entityId,key:a.gwi_metric,name:a.friendly_name || a.gwi_metric,state:state.state,feedback:a.operation_feedback});
    }
  }
  return [...networks.values()].map(n => {
    for(const p of n.points) {
      p.clients.sort((a,b)=>rank[a.signal.key]-rank[b.signal.key] || a.name.localeCompare(b.name,locale));
      p.ratedClients=p.clients.filter(c=>c.signal.key!=="unknown").length;
      p.weakClients=p.clients.filter(c=>c.signal.key==="weak").length;
    }
    const roots=n.points.filter(p=>p.isRoot);
    const root=roots.length===1?roots[0]:null;
    if(root && (root.online!==true || root.unavailable))
      for(const p of n.points.filter(p=>!p.isRoot))p.mesh=quality(null,null,true,locale);
    return { ...n,root,
      // Comparisons to the explicit primary point do not assert intermediate hops.
      meshLinks:root?n.points.filter(p=>p.id!==root.id && p.rootId===root.id).map(p=>({from:root.id,to:p.id,quality:p.mesh})):[],
      ratedClients:n.clients.filter(c=>c.signal.key!=="unknown").length,
      weakClients:n.clients.filter(c=>c.signal.key==="weak").length,
      rssiClients:n.clients.filter(c=>c.signal.rssi!=null).length,
      points:n.points.sort((a,b)=>Number(b.isRoot)-Number(a.isRoot) || a.name.localeCompare(b.name,locale)),
    };
  });
}
