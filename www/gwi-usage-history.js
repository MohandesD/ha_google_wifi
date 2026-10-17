// Display supplied usage buckets; selection and zoom never send a Google action.
const words={
 en:{title:'Network usage',minute:'Minute · 1h',hour:'Hour · 24h',day:'Day · 7d',month:'Day · 30d',download:'Download',upload:'Upload',missing:'Missing buckets are unknown. Totals below cover the supplied records.',empty:'No usage records supplied.',loading:'Loading history…',failed:'History is unavailable. Check Google capabilities.',period:'Requested period',returned:'Buckets returned',time:'Time',data:'Data per interval',hint:'Select a bar to see its interval and exact values. Use the arrow keys to move between intervals.',selected:'Selected interval',select:'Select interval',unknown:'Not supplied',zoom:'Zoom around this interval',reset:'Show full period',zoomed:'Zoomed view',zoomHint:'Zoom uses the supplied intervals; no finer measurements are inferred.',table:'View usage records',interval:'Interval',total:'Total',partial:'available records',previous:'Previous interval',next:'Next interval'},
 pt:{title:'Utilização da rede',minute:'Minuto · 1h',hour:'Hora · 24h',day:'Dia · 7d',month:'Dia · 30d',download:'Download',upload:'Upload',missing:'Os intervalos em falta são desconhecidos. Os totais abaixo abrangem os registos fornecidos.',empty:'Sem registos de utilização.',loading:'A carregar histórico…',failed:'Histórico indisponível. Consulte as capacidades Google.',period:'Intervalo pedido',returned:'Intervalos recebidos',time:'Hora',data:'Dados por intervalo',hint:'Selecione uma barra para ver o intervalo e os valores exatos. Use as setas do teclado para mudar de intervalo.',selected:'Intervalo selecionado',select:'Selecionar intervalo',unknown:'Não fornecido',zoom:'Ampliar junto deste intervalo',reset:'Ver período completo',zoomed:'Vista ampliada',zoomHint:'A ampliação usa os intervalos fornecidos; não são inferidas medições mais detalhadas.',table:'Ver registos de utilização',interval:'Intervalo',total:'Total',partial:'registos disponíveis',previous:'Intervalo anterior',next:'Intervalo seguinte'},
};
const preferences=new Map();
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
const amount=value=>value!==null&&value!==undefined&&typeof value!=='boolean'&&value!==''&&Number.isFinite(Number(value))&&Number(value)>=0?Number(value):null;
const instant=value=>{if(value===null||value===undefined||value===''||typeof value==='boolean')return null;const n=new Date(value).getTime();return Number.isFinite(n)?n:null;};
export function formatBytes(value,language='en'){
 const valueNumber=amount(value);if(valueNumber===null)return '—';
 const units=['B','kB','MB','GB','TB'];let n=valueNumber,i=0;while(n>=1000&&i<units.length-1){n/=1000;i++;}
 return new Intl.NumberFormat(language,{maximumFractionDigits:2}).format(n)+' '+units[i];
}
export function usageRows(series){
 return (Array.isArray(series)?series:[]).filter(r=>r&&instant(r.start)!==null&&instant(r.end)!==null&&instant(r.end)>instant(r.start)).map(r=>({start:new Date(r.start).toISOString(),end:new Date(r.end).toISOString(),download_bytes:amount(r.download_bytes),upload_bytes:amount(r.upload_bytes)})).sort((a,b)=>instant(a.start)-instant(b.start));
}
export function usageScale(maximum){
 if(!(maximum>0))return {maximum:1,step:1};
 const raw=maximum/4,power=10**Math.floor(Math.log10(raw)),step=Math.max(1,[1,2,2.5,5,10].find(n=>n*power>=raw)*power);
 const ceiling=Math.ceil(maximum/step)*step;
 return Number.isFinite(ceiling)?{maximum:ceiling,step}:{maximum,step:maximum/4};
}
const CSS=`
 :host{display:block;min-width:0;max-width:100%;color:var(--primary-text-color);margin:16px 0;font:inherit}
 *{box-sizing:border-box}h3{font-size:16px;margin:0 0 10px}nav,.tools{display:flex;flex-wrap:wrap;gap:7px;align-items:center}
 button,summary{font:inherit;font-size:13px;border:1px solid var(--divider-color,#d5d9df);border-radius:8px;padding:9px 12px;background:var(--card-background-color,#fff);color:inherit;cursor:pointer;min-height:44px}
 button[aria-pressed=true]{border-color:var(--primary-color,#009ac4);background:color-mix(in srgb,var(--primary-color,#009ac4) 9%,var(--card-background-color,#fff));color:var(--primary-color,#009ac4)}
 button:focus-visible,summary:focus-visible,.plot-scroll:focus-visible{outline:3px solid var(--primary-color,#009ac4);outline-offset:2px}button:disabled{opacity:.5;cursor:default}
 p{font-size:12px;color:var(--secondary-text-color);margin:9px 0;line-height:1.5;overflow-wrap:anywhere}.hint{font-size:13px}
 .plot-scroll{max-width:100%;overflow-x:auto;overscroll-behavior-x:contain;border-radius:8px;margin:4px 0 10px;scroll-margin-top:calc(var(--gwi-sticky-offset,0px) + 80px)}
 svg{width:100%;min-width:640px;height:auto;display:block}svg text{fill:var(--secondary-text-color,#66717c);font-size:13px;font-family:inherit}
 .grid{stroke:var(--divider-color,#dde2e7);stroke-width:1;stroke-dasharray:3 4}.axis{stroke:var(--secondary-text-color,#66717c);stroke-width:1}
 .bucket{cursor:pointer;outline:none}.bucket .selection{fill:transparent;stroke:transparent}.bucket:hover .selection{fill:color-mix(in srgb,var(--primary-color,#009ac4) 9%,transparent)}
 .bucket[aria-pressed=true] .selection{fill:color-mix(in srgb,var(--primary-color,#009ac4) 12%,transparent);stroke:var(--primary-color,#009ac4);stroke-width:1.5}.bucket:focus-visible .selection{stroke:var(--primary-text-color,#172033);stroke-width:2}
 .legend{display:flex;flex-wrap:wrap;gap:10px 24px;font-size:13px;line-height:1.6}.legend span{display:inline-flex;align-items:center;gap:7px}.key{display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--primary-color,#009ac4)}.key.upload{background:#9868da}
 .detail{margin:14px 0;padding:14px;border:1px solid var(--primary-color,#009ac4);border-radius:10px;background:color-mix(in srgb,var(--primary-color,#009ac4) 4%,var(--card-background-color,#fff))}.detail h4{font-size:13px;margin:0 0 6px}.detail .period{font-size:14px;color:var(--primary-text-color);margin:0 0 12px}
 .values{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,160px),1fr));gap:12px;margin-bottom:12px}.value-label{font-size:12px;color:var(--secondary-text-color)}.value{font-size:21px;font-variant-numeric:tabular-nums;margin:4px 0}.exact{font-size:11px;color:var(--secondary-text-color);overflow-wrap:anywhere}
 .tools{margin:10px 0}.table-scroll{overflow-x:auto;max-width:100%}details{margin-top:14px}summary{display:list-item;width:fit-content;max-width:100%;padding-inline-start:16px}table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}th,td{text-align:start;padding:8px;border-bottom:1px solid var(--divider-color,#dde2e7)}th{color:var(--secondary-text-color);font-weight:600}td button{font-size:12px;text-align:start;width:100%;border:0;background:transparent;padding:5px;white-space:normal}
`;

export class GwiUsageHistory extends HTMLElement{
 constructor(){super();this.attachShadow({mode:'open'});this._request=0;}
 configure(value){
  this._request++;
  this._config=value;
  if(!preferences.has(value.entityId))preferences.set(value.entityId,{mode:'hour',views:{},cached:{}});
  if(preferences.size>100)preferences.delete(preferences.keys().next().value);
  this._prefs=preferences.get(value.entityId);this._mode=this._prefs.mode;
  this._prefs.cached.hour={series:value.series||[],period:value.summary?.period||value.summary||{}};
  this._data=this._prefs.cached[this._mode]||{series:[],period:{}};this._error=false;this._loading=false;this._render();
  if((this._mode!=='hour'||!value.series?.length)&&value.api?.callWS)this._load(this._mode);
 }
 disconnectedCallback(){this._request++;}
 _view(){return this._prefs.views[this._mode]||= {};}
 _date(value,short=false){
  const opts=short?(this._mode==='day'||this._mode==='month'?{month:'short',day:'2-digit'}:{hour:'2-digit',minute:'2-digit'}):{month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'};
  return new Intl.DateTimeFormat(this._language,{...opts,timeZone:this._config.timeZone||undefined}).format(new Date(value));
 }
 async _load(mode){
  if(!this._config?.api?.callWS)return;
  this._mode=mode;this._prefs.mode=mode;this._data=this._prefs.cached[mode]||{series:[],period:{}};const request=++this._request;
  this._loading=true;this._error=false;this._render();
  try{
   const result=await this._config.api.callWS({type:'call_service',domain:'google_wifi_insights',service:'get_usage_history',service_data:{entity_id:this._config.entityId,resolution:mode},return_response:true});
   if(request!==this._request)return;
   this._data=result.response;this._error=!Array.isArray(this._data?.series);if(!this._error)this._prefs.cached[mode]=this._data;
  }catch{if(request===this._request)this._error=true;}
  finally{if(request===this._request){this._loading=false;this._render();}}
 }
 _select(row,focus=false){
  const view=this._view();view.selected=row.start;
  if(view.zoom&&(instant(row.start)<instant(view.zoom.start)||instant(row.end)>instant(view.zoom.end)))view.zoom=null;
  this._render();
  if(focus)[...this.shadowRoot.querySelectorAll('.bucket')].find(n=>n.getAttribute('data-start')===row.start)?.focus?.({preventScroll:true});
 }
 _zoom(row,rows){
  const index=rows.findIndex(r=>r.start===row.start),start=Math.max(0,Math.min(rows.length-5,index-2)),window=rows.slice(start,start+5);
  this._view().zoom={start:window[0].start,end:window.at(-1).end};this._render();this.shadowRoot.querySelector('.plot-scroll')?.scrollIntoView?.({block:'start',behavior:'instant'});
 }
 _button(text,run){const b=el('button',text);b.type='button';b.addEventListener('click',run);return b;}
 _svg(tag,attributes={},text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attributes))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;}
 _render(){
  if(!this._config)return;
  this._language=this._config.language==='pt'?'pt':'en';const t=words[this._language],data=this._data||{},view=this._view();
  const scroll=this.shadowRoot.querySelector('.plot-scroll')?.scrollLeft??view.scroll??0;
  this.shadowRoot.replaceChildren(el('style',CSS),el('h3',t.title));
  const nav=el('nav');nav.setAttribute('aria-label',t.period);
  for(const mode of ['minute','hour','day','month']){const b=this._button(t[mode],()=>this._load(mode));b.setAttribute('aria-pressed',String(mode===this._mode));b.disabled=this._loading||!this._config.api?.callWS;nav.append(b);}
  this.shadowRoot.append(nav);
  if(this._loading){this.shadowRoot.append(el('p',t.loading));if(!data.series?.length)return;}
  if(this._error){this.shadowRoot.append(el('p',t.failed));return;}
  const rows=usageRows(data.series);
  if(!rows.length){this.shadowRoot.append(el('p',t.empty));return;}
  const periodStart=instant(data.period?.start)??instant(rows[0].start),periodEnd=instant(data.period?.end)??instant(rows.at(-1).end);
  if(!(periodEnd>periodStart)){this.shadowRoot.append(el('p',t.empty));return;}
  const selected=rows.find(r=>r.start===view.selected);if(!selected)view.selected=null;
  let start=periodStart,end=periodEnd,visible=rows;
  if(view.zoom){start=instant(view.zoom.start);end=instant(view.zoom.end);visible=rows.filter(r=>instant(r.start)>=start&&instant(r.end)<=end);if(!visible.length){view.zoom=null;start=periodStart;end=periodEnd;visible=rows;}}
  visible=visible.filter(r=>instant(r.end)>start&&instant(r.start)<end);
  const hint=el('p',t.hint);hint.className='hint';this.shadowRoot.append(hint);
  const scroller=el('div');scroller.className='plot-scroll';scroller.setAttribute('role','region');scroller.setAttribute('aria-label',t.title);scroller.tabIndex=0;
  const svg=this._svg('svg',{viewBox:'0 0 800 260',role:'group','aria-label':t.title});
  const left=78,right=778,top=34,bottom=202,width=right-left,height=bottom-top;
  const maximum=Math.max(0,...visible.flatMap(r=>[r.download_bytes??0,r.upload_bytes??0])),scale=usageScale(maximum),position=value=>left+(value-start)/(end-start)*width;
  svg.append(this._svg('text',{x:left,y:17},t.data));
  for(let index=0;index<=Math.round(scale.maximum/scale.step);index++){const tick=index*scale.step,y=bottom-tick/scale.maximum*height;svg.append(this._svg('line',{x1:left,y1:y,x2:right,y2:y,class:'grid'}),this._svg('text',{x:left-10,y:y+4,'text-anchor':'end',class:'y-tick'},formatBytes(tick,this._language)));}
  svg.append(this._svg('line',{x1:left,y1:bottom,x2:right,y2:bottom,class:'axis'}));
  for(let index=0;index<=4;index++){const value=start+(end-start)*index/4,x=position(value);svg.append(this._svg('line',{x1:x,y1:bottom,x2:x,y2:bottom+5,class:'axis'}),this._svg('text',{x,y:bottom+24,'text-anchor':index===0?'start':index===4?'end':'middle',class:'x-tick'},this._date(value,true)));}
  svg.append(this._svg('text',{x:(left+right)/2,y:251,'text-anchor':'middle'},t.time+(this._config.timeZone?' · '+this._config.timeZone:'')));
  visible.forEach((row,index)=>{
   const x=Math.max(left,position(instant(row.start))),finish=Math.min(right,position(instant(row.end))),slot=Math.max(1,finish-x),isSelected=view.selected===row.start;
   const values=['download','upload'].map(direction=>t[direction]+': '+(row[direction+'_bytes']===null?t.unknown:formatBytes(row[direction+'_bytes'],this._language)));
   const group=this._svg('g',{class:'bucket',role:'button',tabindex:isSelected||!view.selected&&index===0?0:-1,'aria-pressed':isSelected,'aria-label':t.select+' · '+this._date(row.start)+' – '+this._date(row.end)+' · '+values.join(' · '),'data-start':row.start});
   group.append(this._svg('title',{},this._date(row.start)+' – '+this._date(row.end)+' · '+values.join(' · ')),this._svg('rect',{x,y:top-4,width:slot,height:height+8,rx:3,class:'selection'}));
   ['download','upload'].forEach((direction,i)=>{const value=row[direction+'_bytes'];if(value===null)return;const barHeight=value/scale.maximum*height;group.append(this._svg('rect',{x:x+i*slot/2+1,y:bottom-barHeight,width:Math.max(0.5,slot/2-2),height:barHeight,fill:i?'#9868da':'var(--primary-color,#009ac4)','pointer-events':'none'}));});
   group.addEventListener('click',()=>this._select(row,true));
   group.addEventListener('keydown',event=>{const next={ArrowLeft:Math.max(0,index-1),ArrowRight:Math.min(visible.length-1,index+1),Home:0,End:visible.length-1}[event.key];if(next!==undefined){event.preventDefault();this._select(visible[next],true);}else if(event.key==='Enter'||event.key===' '){event.preventDefault();this._select(row,true);}});
   svg.append(group);
  });
  scroller.append(svg);this.shadowRoot.append(scroller);scroller.scrollLeft=scroll;scroller.addEventListener('scroll',()=>{view.scroll=scroller.scrollLeft;});
  const legend=el('div');legend.className='legend';
  for(const direction of ['download','upload']){const supplied=rows.map(r=>r[direction+'_bytes']).filter(v=>v!==null),total=supplied.length?supplied.reduce((a,b)=>a+b,0):null;const text=el('span'),key=el('i');key.className='key '+direction;key.setAttribute('aria-hidden','true');text.append(key,document.createTextNode(t[direction]+': '+formatBytes(total,this._language)+(supplied.length<rows.length?' · '+t.partial:'')));legend.append(text);}
  this.shadowRoot.append(legend);
  if(view.zoom){const tools=el('div');tools.className='tools';tools.append(el('span',t.zoomed),this._button(t.reset,()=>{view.zoom=null;this._render();}));this.shadowRoot.append(tools,el('p',t.zoomHint));}
  if(selected)this._detail(selected,rows,t);
  const expected=data.period?.granularity_seconds?Math.floor((periodEnd-periodStart)/1000/data.period.granularity_seconds):data.period?.expected_buckets;
  this.shadowRoot.append(el('p',t.period+': '+this._date(periodStart)+' – '+this._date(periodEnd)),el('p',t.returned+': '+rows.length+(expected?' / '+expected:'')));
  if(expected&&rows.length<expected)this.shadowRoot.append(el('p',t.missing));
  this._table(rows,t);
 }
 _detail(row,rows,t){
  const detail=el('section');detail.className='detail';detail.setAttribute('aria-label',t.selected);detail.setAttribute('aria-live','polite');
  detail.append(el('h4',t.selected));const period=el('p',this._date(row.start)+' – '+this._date(row.end));period.className='period';detail.append(period);
  const values=el('div');values.className='values';
  for(const direction of ['download','upload','total']){const value=direction==='total'?(row.download_bytes!==null&&row.upload_bytes!==null?row.download_bytes+row.upload_bytes:null):row[direction+'_bytes'];const cell=el('div'),label=el('div',t[direction]),amount=el('div',value===null?t.unknown:formatBytes(value,this._language));label.className='value-label';amount.className='value';cell.append(label,amount);if(value!==null&&value>=1000){const exact=el('div',new Intl.NumberFormat(this._language).format(value)+' B');exact.className='exact';cell.append(exact);}values.append(cell);}
  detail.append(values);const controls=el('div');controls.className='tools';const index=rows.indexOf(row);
  const previous=this._button('← '+t.previous,()=>this._select(rows[index-1]));previous.disabled=index===0;
  const next=this._button(t.next+' →',()=>this._select(rows[index+1]));next.disabled=index===rows.length-1;controls.append(previous,next);
  if(!this._view().zoom&&rows.length>5)controls.append(this._button(t.zoom,()=>this._zoom(row,rows)));
  detail.append(controls);this.shadowRoot.append(detail);
 }
 _table(rows,t){
  const view=this._view(),details=el('details'),summary=el('summary',t.table);details.open=!!view.table;
  details.addEventListener('toggle',()=>{if(details.isConnected)view.table=details.open;});details.append(summary);
  const wrapper=el('div');wrapper.className='table-scroll';const table=el('table'),head=el('thead'),heading=el('tr');
  for(const label of [t.interval,t.download,t.upload]){const th=el('th',label);th.scope='col';heading.append(th);}head.append(heading);table.append(head);
  const body=el('tbody');for(const row of rows){const tr=el('tr'),cell=el('td');cell.append(this._button(this._date(row.start)+' – '+this._date(row.end),()=>this._select(row)));tr.append(cell,el('td',formatBytes(row.download_bytes,this._language)),el('td',formatBytes(row.upload_bytes,this._language)));body.append(tr);}table.append(body);wrapper.append(table);details.append(wrapper);this.shadowRoot.append(details);
 }
}
if(!customElements.get('gwi-usage-history'))customElements.define('gwi-usage-history',GwiUsageHistory);
