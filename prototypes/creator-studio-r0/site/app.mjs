import { initial, nav, poster, storyboard } from './fixtures.mjs';

let s = initial(), pending, trigger;
const $ = (id) => document.getElementById(id);
const main = $('main'), dialog = $('action');
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const route = () => location.hash.startsWith('#/') ? location.hash.slice(2).split('/') : ['mission'];
const btn = (label, action, id = '', extra = '') => `<button type="button" data-act="${action}" data-id="${id}" ${extra}>${label}</button>`;
const link = (label, path, cls = '') => `<a class="${cls}" href="#/${path}">${label}</a>`;
const chip = (text, tone = '') => `<span class="chip ${tone}">${esc(text)}</span>`;
const heading = (eyebrow, title, text) => `<header class="heading"><p class="eyebrow">${eyebrow}</p><h1 tabindex="-1">${title}</h1><p>${text}</p></header>`;
const tabs = (base, items, active) => `<nav class="tabs" aria-label="Workspace sections">${items.map(([id,label]) => `<a href="#/${base}/${id}" ${id===active?'aria-current="page"':''}>${label}</a>`).join('')}</nav>`;
const options = (items, current) => items.map(item=>`<option${item===current?' selected':''}>${esc(item)}</option>`).join('');
const jobPath = (j, tab='overview') => `jobs/${j.id}/${tab}`;
const groups = (events) => `<ol class="activity">${events.map(([time,text,id])=>`<li><time>${time}</time><span>${text}<small>${id}</small></span></li>`).join('')}</ol>`;
const card = (job) => `<article class="card">${poster(job.art)}<div class="pad"><p class="eyebrow">${job.format}</p><h2>${link(esc(job.title),jobPath(job))}</h2>${chip(job.execution)} ${chip(`QA: ${job.qa}`)} ${chip(`Creative: ${job.creative}`)} ${chip(s.exports.has(job.id)?'Simulated export recorded':job.eligible?'Export eligible':'Export blocked')}${job.execution==='Rendered'||job.qa==='Fail'?`<label class="select-cut"><input type="checkbox" data-export="${job.id}" ${s.exportSelection.has(job.id)?'checked':''}> Include in export plan</label>`:''}</div></article>`;
const routeViews = new Map();

function mission() {
  return `${heading('STUDIO / TODAY','Mission Control','Start with the work that needs your judgment.')}<section class="feature"><div class="feature-copy"><p class="eyebrow">FEATURED CUT / 03</p><h2>How canal locks<br>lift boats</h2><p>A long-form waterway explainer. The composition is ready for a fixture review.</p>${link('Open composition review','review/composition','primary')}</div><div class="feature-poster">${poster('lock')}<span>FRAME STUDY / CANAL CHAMBER</span></div></section><div class="split"><section class="panel"><h2>Needs you</h2><ul class="actions"><li>${link('Review the canal composition','review/composition')} ${chip('Awaiting review')}</li><li>${link('Diagnose missing word timing','jobs/fixture-map/logs')} ${chip('Failed','warn')}</li><li>${link('Check independent batch blockers','batch/fixture-b20/validate')} ${chip('20 ideas')}</li></ul></section><section class="panel"><h2>Recent fixture activity</h2>${groups(s.activity)}</section></div>`;
}
function create() {
  const conditional = s.format.startsWith('Long'), complete = Boolean(s.title.trim() && s.detail.trim().length >= 8 && !conditional);
  return `${heading('INTAKE / BRIEF','Universal Create','Choose an input and see what the sample workflow can support.')}<div class="split"><section class="panel"><h2>Source and brief</h2><label>Input <select id="source">${options(['Topic','Script','Files','Reference'],s.source)}</select></label><p>${{Topic:'A topic needs production detail before it becomes a fixture spec.',Script:'Describe the sample narration in the production detail field.',Files:'Using a preselected local fixture illustration. No file picker or upload.',Reference:'Using an original fixture storyboard as inspiration. No reference analysis is run.'}[s.source]}</p><label>Target <select id="format">${options(['Shorts · 9:16','Long-form · 16:9'],s.format)}</select></label><label>Working title <input id="title-field" maxlength="90" value="${esc(s.title)}"></label><label>Production detail <textarea id="detail" maxlength="400" rows="3" placeholder="Opening image and narration direction">${esc(s.detail)}</textarea></label>${btn('Simulate validate','validate-create','','class="primary"')}</section><section class="panel"><p class="eyebrow">PROPOSED TRACK</p><h2>${conditional?'Director-led · Track B':'Spec-driven · Track A'}</h2>${chip(conditional?'Conditional handoff':'Fixture workflow',conditional?'warn':'')}<p>${conditional?'A director must prepare the long-form composition. This example cannot be saved as a ready job.':'Add a title and at least eight characters of production detail to complete this sample spec.'}</p>${s.checked?`<p role="status">${complete?'Fixture spec validated.':conditional?'Blocked: director composition required.':'Incomplete: add a title and production detail.'}</p>`:''}${s.checked&&complete?btn('Simulate save draft','save-create','','class="primary"'):''}</section></div>`;
}
function batches(tab) {
  return `${heading('PLANNING / GROUPS','Batch Studio','Independent jobs and pinned series revisions, side by side.')}${tabs('batch',[['independent','Independent'],['series','Series']],tab==='series'?'series':'independent')}<div class="card collection">${poster(tab==='series'?'lock':'map')}<div class="pad"><p class="eyebrow">${tab==='series'?'SERIES / 20 EPISODES':'INTAKE / 20 IDEAS'}</p><h2>${tab==='series'?'Inside the waterways':'Mixed slate / November'}</h2>${link(tab==='series'?'Open campaign':'Open batch',tab==='series'?'campaign/fixture-canals/brief':'batch/fixture-b20/intake','primary')}</div></div>`;
}
function batch(tab) {
  const t = ['intake','validate','monitor'].includes(tab)?tab:'intake';
  const ready = s.rows.filter(r=>r.state==='Ready');
  const receipts = s.receipt?.map(([id,outcome])=>`<li>${esc(s.rows.find(r=>r.id===id).title)}: ${outcome}</li>`).join('') ?? '';
  const controls = s.validated && t!=='intake' ? `${btn('Select ready rows','select-ready')} ${btn('Clear selection','clear-selection')} ${btn('Simulate submit selected','batch-submit','','class="primary"')} ${btn('Simulate interrupted response','batch-interrupt')} ${btn('Recover session receipt','batch-recover','','')}`:'';
  return `${heading('BATCH / FIXTURE-B20','Mixed slate / November','20 unrelated ideas. Submission and recovery are simulated per row.')}${tabs('batch/fixture-b20',[['intake','Intake'],['validate','Validate'],['monitor','Monitor']],t)}<section class="panel"><h2>${t==='monitor'?'Row receipts':'Intake readiness'}</h2><p role="status">${ready.length} ready · ${s.selected.size} selected · ${s.rows.filter(r=>r.state==='Submitted').length} simulated submissions</p><div class="controls">${btn('Simulate validate batch','batch-validate')} ${controls}</div>${s.interrupted?'<p role="status">Response interrupted. Recover its session receipt before retrying.</p>':receipts?`<ul>${receipts}</ul>`:''}${s.rows.some(r=>r.state==='Stale')&&s.receipt?btn('Simulate revalidate unaccepted rows','batch-revalidate'):''}</section><table class="rows"><thead><tr><th scope="col">Select</th><th scope="col">Idea</th><th scope="col">Target and voice</th><th scope="col">State / detail</th></tr></thead><tbody>${s.rows.map(r=>`<tr><td>${r.state==='Ready'&&s.validated?`<input type="checkbox" aria-label="Select ${esc(r.title)}" data-row="${r.id}" ${s.selected.has(r.id)?'checked':''}>`:'<span aria-hidden="true">·</span>'}</td><th scope="row">${esc(r.title)}<small>${r.id}</small></th><td>${r.format} · ${r.language}</td><td>${chip(r.state,r.state==='Blocked'||r.state==='Stale'?'warn':'')} <small>${esc(r.issue)}</small>${r.state==='Invalid'?btn('Simulate resolve missing detail','fix-row',r.id):''}</td></tr>`).join('')}</tbody></table>`;
}
function campaign(tab) {
  const t = ['episodes','assets','history'].includes(tab)?tab:'brief';
  const body = t==='episodes'?`<h2>Episode slate</h2><ul class="actions">${s.episodes.map((e,i)=>`<li><strong>${String(i+1).padStart(2,'0')} / ${esc(e.title)}</strong><div>${chip(e.status)} ${chip(`Pinned ${e.revision}`)}<small>${e.language} · ${e.voice} · ${e.asset}</small>${i===0?'<small>Reviewed at r2; newer defaults do not apply.</small>':i===1?'<small>Missing original asset. Restore identical bytes or rebase an eligible draft.</small>':i===4?'<small>Required voice is cleared; no fallback.</small>':i===3&&!s.rebased?btn('Preview draft rebase','rebase',e.id):''}</div></li>`).join('')}</ul>`:t==='assets'?`<h2>Pinned asset identities</h2>${s.assets.map(a=>`<p><strong>${a.name}</strong><br>${a.digest} · ${a.availability}</p>`).join('')}`:t==='history'?`<h2>Revision history</h2><p>r2 · original brief and first logo</p><p>r3 · revised logo, brand defaults for new drafts</p>${s.rebased?`<p>Episode 04: prior ${s.rebased.revision} kept ${s.rebased.asset}; draft r3.1 pins fixture-logo-b.</p>`:''}`:`<h2>Inside the waterways</h2><p>20 episodes around the design of canals. Brand direction: illustrated cutaways, teal waterlines and a warm narrator.</p><p>Defaulted target: long-form · 16:9. Inherited voice: Narrator. Current defaults: r3. Legacy episode pins stay at r2.</p>${link('Inspect episode overrides','campaign/fixture-canals/episodes','primary')}`;
  return `${heading('SERIES / CAMPAIGN','Inside the waterways','Pinned creative direction, explicit overrides and reviewed history.')}${tabs('campaign/fixture-canals',[['brief','Brief'],['episodes','Episodes'],['assets','Assets'],['history','History']],t)}<section class="panel">${body}</section>`;
}
function library() {
  const axes = [['execution','Execution',['Rendered','Failed','Draft','Queued']],['qa','Technical QA',['Pass','Fail','Not run']],['creative','Creative',['Changes requested','Accepted','Not requested']],['eligible','Export',['Eligible','Blocked']]];
  const jobs = s.jobs.filter(j=>axes.every(([k])=>!s.filters[k]||s.filters[k]==='All'||s.filters[k]===(k==='eligible'?(j.eligible?'Eligible':'Blocked'):j[k])));
  return `${heading('CATALOGUE / CUTS','Video Library','Find a cut by what has actually happened in this fixture.') }<section class="panel"><div class="controls filters">${axes.map(([k,label,values])=>`<label>${label}<select data-filter="${k}">${options(['All',...values],s.filters[k]??'All')}</select></label>`).join('')}</div><div class="controls">${btn(s.list?'Show poster grid':'Show list','view-toggle')} ${btn('Preview fixture export plan','export-plan')}</div></section><div class="${s.list?'card-list':'cards'}">${jobs.map(card).join('')||'<p>No cuts match these filters.</p>'}</div>${s.exportReceipt?`<section class="panel"><h2>Simulated export receipt</h2>${s.exportReceipt}</section>`:''}`;
}
function job(j, tab) {
  if (!j) return notFound();
  const sections = ['Overview','Brief','Script','Composition','Review','Files','Logs'];
  const body = {brief:`<h2>Creative brief</h2><p>${esc(j.detail??'Explain the idea in a short visual sequence, with one concrete example.')}</p>`,script:`<h2>Script / sample copy</h2><p>Start with a visible question. Show the mechanism. End with what changed.</p>`,composition:`<h2>Composition evidence</h2><figure>${poster(j.art)}<figcaption>Original fixture poster; not a rendered video.</figcaption></figure>`,review:`<h2>Review evidence</h2><p>Technical QA: ${j.qa}. Creative: ${j.creative} (advisory). Export: ${j.eligible?'eligible':'blocked'}.</p>${j.id==='fixture-canal'?link('Open exact subject','review/composition','primary'):''}`,files:'<h2>Fixture artifacts</h2><p>Sample poster and stage receipt only. No production paths or downloads.</p>',logs:`<h2>Attempt history</h2><ul>${j.attempts.map(a=>`<li>${a}</li>`).join('')}</ul>${j.execution==='Failed'?btn('Preview retry and invalidation','retry',j.id,'class="primary"'):j.execution==='Queued'?'<p>Retry unavailable while the fixture attempt is active.</p>':''}`,overview:`<h2>Stage overview</h2><ol class="stages"><li>Brief · ${j.specRevision}</li><li>Script · ${j.execution==='Draft'?'not reviewed':'fixture evidence'}</li><li>Composition · ${j.execution}</li><li>Technical QA · ${j.qa}</li></ol>`}[tab]??'';
  return `${heading(`VIDEO / ${j.id.toUpperCase()}`,esc(j.title),`${j.format} · ${j.language} · ${j.track}`)}${tabs(`jobs/${j.id}`,sections.map(a=>[a.toLowerCase(),a]),tab)}<div class="split"><section class="panel">${body||'<h2>Stage not found</h2>'}</section><aside class="card">${poster(j.art)}<div class="pad"><h2>Current state</h2>${chip(j.execution)} ${chip(`QA: ${j.qa}`)}<p>Creative: ${j.creative}</p></div></aside></div>`;
}
function creative(tab) {
  const t = ['effects','voices','assets'].includes(tab)?tab:'looks';
  const names = {looks:['Tidal Cut','Violet Grid','Warm Archive'],effects:['Waterline reveal','Focus cut','Graphic wipe'],voices:['English narrator','Hindi narrator','Alternate voice'],assets:['Series logo / revised','Nearest-neighbor plate','Gain and loss chart']}[t];
  return `${heading('TOOLKIT / CATALOGUE','Creative Library','Browse ideas and evidence, not a promise that every look can render.')}${tabs('creative',[['looks','Looks'],['effects','Effects'],['voices','Voices'],['assets','Assets']],t)}<div class="cards">${names.map((name,i)=>`<article class="card">${poster(['lock','map','gain'][i])}<div class="pad"><h2>${name}</h2><details><summary>Capability evidence</summary><p>Registry: fixture entry · Compile: ${i===0?'fixture checked':'unknown'} · Builder consumption: unknown · Verified frames: none.</p></details>${btn('Simulate apply to draft','apply',String(i),`data-name="${name}"`)}</div></article>`).join('')}</div>${s.applied?`<p role="status">${esc(s.applied)} attached to the in-memory draft. No render occurred.</p>`:''}`;
}
const frames = ['The boat enters the low chamber.', 'The closed gates let the chamber water rise.', 'Equal levels let the boat leave upstream.'];
function review(tab) {
  const gate = tab==='script'?'Script':'Composition';
  const key = gate.toLowerCase();
  return `${heading('SCREENING / EXACT SUBJECT','Review Studio','Check the fixture revision before recording a simulated grant.')}${tabs('review',[['composition','Composition'],['script','Script']],key)}<div class="split review"><section class="panel"><p class="eyebrow">${gate.toUpperCase()} / CANAL LOCKS</p><h2>How canal locks lift boats</h2><p>Revision <code>r${s.revision}</code> · <code>fixture-${key}-r${s.revision}</code></p>${key==='script'?'<blockquote>A lock moves a boat between different water levels. Both gates close while the chamber fills.</blockquote>':`<figure><div id="frame-art">${storyboard(s.frame)}</div><figcaption id="frame-text">${frames[s.frame]}</figcaption></figure><label>Storyboard frame <input id="frame" type="range" min="0" max="2" value="${s.frame}"></label><details><summary>Fixture transcript</summary><ol>${frames.map(f=>`<li>${f}</li>`).join('')}</ol></details>`}<details><summary>Compare with prior revision</summary><p>${s.revision===1?'First fixture subject.':'The same bytes can reappear under a newer revision; the old grant stays stale.'}</p></details></section><aside class="panel"><h2>Review evidence</h2><p>${chip('Technical QA: Pass')} ${chip('Creative: Changes requested','warn')}</p><p>Creative feedback is advisory. This sample remains technically export eligible.</p><p>${s.grants[key]===s.revision?'Simulated grant recorded for current revision.':s.grants[key]?'Prior simulated grant is stale.':'No simulated grant for this revision.'}</p>${btn('Review exact fixture subject','approve',key,'class="primary"')}</aside></div>`;
}
function operations() {
  return `${heading('OBSERVE / PRODUCTION DESK','Operations &amp; Agents','Read fixture receipts and blockers. No running agents or workers are connected.')}<div class="split"><section class="panel"><h2>Production visibility</h2><p role="status">${s.connection??'Last observed 14:22 · fixture snapshot'}</p><div class="controls">${btn('Simulate disconnected','disconnect')} ${btn('Simulate unknown state','unknown')} ${btn('Simulate reconnect','reconnect')}</div><ul class="actions">${s.jobs.map(j=>`<li>${link(esc(j.title),jobPath(j,'logs'))} ${chip(j.execution)}</li>`).join('')}</ul></section><section class="panel"><h2>Agent handoff receipts</h2><p>Recorded sample events, not live agent activity.</p>${groups(s.activity)}</section></div>`;
}
function notFound() { return `${heading('FIXTURE / ROUTE','Fixture not found','This destination does not exist in the prototype.')}${link('Back to Mission Control','mission','primary')}`; }
function render(moveFocus=false) {
  const [page,id,tab] = route();
  const active = page==='jobs'?'library':page==='campaign'?'batch':page;
  const navHtml = nav.map(([key,label,icon])=>`<a href="#/${key}" ${key===active?'aria-current="page"':''}><span aria-hidden="true">${icon}</span><span>${label}</span></a>`).join('');
  $('nav').innerHTML = navHtml;
  $('menu').querySelector('nav').innerHTML=navHtml;
  const pages = {mission,create,batch:()=>id==='fixture-b20'?batch(tab):!id||['independent','series'].includes(id)?batches(id):notFound(),campaign:()=>id==='fixture-canals'?campaign(tab):notFound(),library,jobs:()=>job(s.jobs.find(j=>j.id===id),tab??'overview'),creative:()=>creative(id),review:()=>review(id),operations};
  main.innerHTML = (Object.hasOwn(pages,page)?pages[page]:notFound)();
  if (moveFocus) main.querySelector('h1').focus({preventScroll:true});
}
function changeView() {
  if (location.hash==='#main') { main.focus(); return; }
  if ($('menu').open) $('menu').close();
  if (dialog.open) dialog.close();
  const key = location.hash;
  render(true);
  const previous = routeViews.get(key);
  window.scrollTo(0,previous??0);
}
window.addEventListener('hashchange',changeView);
window.addEventListener('scroll',()=>routeViews.set(location.hash,window.scrollY),{passive:true});
function update(focus) {
  render();
  if (focus) (Array.from(main.querySelectorAll('button,select,input')).find(node => node.dataset.act===focus.dataset.act && node.dataset.id===focus.dataset.id && node.id===focus.id && node.dataset.filter===focus.dataset.filter && node.dataset.row===focus.dataset.row && node.dataset.export===focus.dataset.export) ?? main.querySelector('h1')).focus({preventScroll:true});
}
function alertText(text) { $('notice').textContent = text; }
function modal(button,title,body,confirm,action,suffix='') {
  trigger=button; pending=action;
  dialog.innerHTML=`<h2 id="action-title" tabindex="-1">${title}</h2>${body}<p id="modal-status" role="status"></p><div class="controls"><button data-close type="button">Cancel</button>${suffix}<button data-confirm class="primary" type="button">${confirm}</button></div>`;
  dialog.showModal(); $('action-title').focus();
}
dialog.addEventListener('close',()=>{ pending=null; if(trigger?.isConnected)trigger.focus(); });
$('open-nav').onclick=()=>$('menu').showModal();
$('theme').onclick=()=>{ const light=document.documentElement.classList.toggle('light'); $('theme').textContent=light?'Dark theme':'Light theme'; };
$('reset').onclick=()=>location.reload();
main.addEventListener('input',e=>{if(e.target.id==='title-field'||e.target.id==='detail'){s[e.target.id==='title-field'?'title':'detail']=e.target.value;s.checked=false;main.querySelector('[data-act="save-create"]')?.remove(); main.querySelector('[role="status"]')?.remove();} if(e.target.id==='frame'){s.frame=Number(e.target.value); $('frame-art').innerHTML=storyboard(s.frame); $('frame-text').textContent=frames[s.frame];}});
main.addEventListener('change',e=>{
  const n=e.target;
  if(n.id==='format'||n.id==='source') { s[n.id]=n.value; s.checked=false; }
  else if(n.dataset.filter) s.filters[n.dataset.filter]=n.value;
  else if(n.dataset.row) n.checked?s.selected.add(n.dataset.row):s.selected.delete(n.dataset.row);
  else if(n.dataset.export) n.checked?s.exportSelection.add(n.dataset.export):s.exportSelection.delete(n.dataset.export);
  else return;
  update(n);
});
function submit(interrupted) {
  const selected = s.rows.filter(r=>s.selected.has(r.id)&&r.state==='Ready');
  if (!selected.length) {
    if (s.receipt && !s.interrupted) alertText(`Replayed ${s.receipt.length} existing row outcomes; no new submissions.`);
    else alertText('No new ready rows, or a receipt needs recovery first.');
    return;
  }
  if (s.interrupted) { alertText('Recover the interrupted response before submitting more rows.'); return; }
  s.receipt = selected.map((r,i)=>{
    const drift=!s.drifted&&i===0;
    r.state=drift?'Stale':'Submitted'; r.issue=drift?'Voice runtime changed since validation. Spec remains r1.':'';
    return [r.id,drift?'Blocked by capability drift':'Simulated submission accepted'];
  });
  s.drifted=true; s.selected.clear(); s.interrupted=interrupted;
}
document.addEventListener('click',e=>{
  const b=e.target.closest('button'); if(!b)return;
  if(b.hasAttribute('data-close')) {b.closest('dialog').close();return;}
  if(b.hasAttribute('data-confirm')) {pending?.(); dialog.close(); update(trigger);return;}
  const {act,id}=b.dataset;
  switch(act){
    case 'validate-create':s.checked=true;break;
    case 'save-create':{
      if(!s.checked||!s.title.trim()||s.detail.trim().length<8||s.format.startsWith('Long'))return;
      const j={id:`fixture-draft-${s.jobs.length}`,title:s.title,detail:s.detail,art:'map',format:s.format,language:'English',track:'Track A',specRevision:'r1',execution:'Draft',qa:'Not run',creative:'Not requested',eligible:false,attempts:['01 · Fixture draft saved']}; s.jobs.push(j);location.hash=`#/${jobPath(j)}`;return;
    }
    case 'batch-validate':s.validated=true;if(route()[2]!=='validate'){location.hash='#/batch/fixture-b20/validate';return;}break;
    case 'fix-row':{const r=s.rows.find(a=>a.id===id);r.state='Ready';r.issue='Corrected fixture production detail';break;}
    case 'select-ready':s.selected=new Set(s.rows.filter(r=>r.state==='Ready').map(r=>r.id));break;
    case 'clear-selection':s.selected.clear();break;
    case 'batch-submit':case 'batch-interrupt':submit(act==='batch-interrupt');break;
    case 'batch-recover':s.interrupted=false;break;
    case 'batch-revalidate':for(const r of s.rows)if(r.state==='Stale'){r.state='Ready';r.issue='Fixture capability available again; spec unchanged';}break;
    case 'rebase':return modal(b,'Preview a draft rebase','<p>Episode 04 keeps Hindi. Compare first logo <code>fixture-digest-a</code> → revised <code>fixture-digest-b</code>. Reviewed episode 01 remains at r2.</p>','Simulate rebase',()=>{const ep=s.episodes.find(a=>a.id===id);s.rebased={...ep};ep.revision='r3.1';ep.asset='fixture-logo-b';});
    case 'view-toggle':s.list=!s.list;break;
    case 'apply':s.applied=b.dataset.name;break;
    case 'approve':{const rev=s.revision;return modal(b,'Confirm exact fixture subject',`<p>Canal locks · ${esc(id)} · revision r${rev} · fixture-${id}-r${rev}</p><p>Simulated local operator. Not an authenticated identity or real grant.</p>`,'Simulate grant',()=>{if(rev===s.revision)s.grants[id]=rev;},btn('Simulate newer revision','new-subject'));}
    case 'new-subject':s.revision++;$('modal-status').textContent='Subject changed. Close and reopen to review the current revision.';dialog.querySelector('[data-confirm]').disabled=true;return;
    case 'export-plan':{
      const selected=s.jobs.filter(j=>s.exportSelection.has(j.id));
      if(!selected.length){alertText('Select at least one cut for a fixture export plan.');return;}
      const list=describe=>`<ul>${selected.map(j=>`<li>${esc(j.title)}: ${describe(j)}</li>`).join('')}</ul>`;
      return modal(b,'Fixture export preflight',list(j=>j.eligible?'Technically eligible. Creative feedback advisory.':'Skipped: not technically eligible.'),'Simulate export selected',()=>{
        s.exportReceipt=list(j=>{if(!j.eligible)return 'skipped (QA).';if(j.id==='fixture-gain')return 'failed (destination conflict).';s.exports.add(j.id);return 'simulated export successful.';});
      });
    }
    case 'retry':return modal(b,'Preview retry scope','<p>Retry Align for this fixture job only. Any downstream composition and QA evidence becomes not current. Attempt 01 remains in history.</p>','Simulate retry',()=>{const j=s.jobs.find(a=>a.id===id);j.execution='Queued';j.qa='Not run';j.attempts.push('02 · Align retry queued in fixture');});
    case 'disconnect':s.connection='Disconnected · last observed 14:22';break;
    case 'unknown':s.connection='Unknown · no current worker evidence';break;
    case 'reconnect':s.connection='Last observed 14:23 · refreshed fixture snapshot';break;
    default:return;
  }
  update(b);
});
render();
