import assert from 'node:assert/strict';
import { once } from 'node:events';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdir, realpath } from 'node:fs/promises';
import { request } from 'node:http';
import { createRequire } from 'node:module';
import { isAbsolute, resolve, sep, join } from 'node:path';
import { fixtureServer, origin, paths, start } from './serve.mjs';

const [modules, output, executablePath] = process.argv.slice(2);
assert(modules && output && isAbsolute(modules) && isAbsolute(output), 'Pass absolute paths to existing node_modules and an outside-Git output directory');
const repo = execFileSync('git', ['rev-parse','--show-toplevel'], {encoding:'utf8'}).trim();
const parent = await realpath(resolve(output,'..'));
const outputPath = join(parent, output.split(sep).at(-1));
assert(outputPath!==repo && !outputPath.startsWith(`${repo}${sep}`));
await mkdir(outputPath); // Require a new directory; never overwrite evidence.
const require = createRequire(join(modules,'fixture-check.cjs'));
const { chromium } = require('playwright');
const axePath = require.resolve('axe-core/axe.min.js');
const lsof=spawnSync('/usr/sbin/lsof',['-nP','-iTCP:4310','-sTCP:LISTEN'],{encoding:'utf8'});
assert.equal(lsof.status,1,'Default live Studio port is not clear, or lsof failed');
const ps=execFileSync('/bin/ps',['-axo','command'],{encoding:'utf8'});
assert(!ps.split('\n').some(line=>/(contentos\.dashboard|contentos(?:\.sh)?\s+dashboard\b)/.test(line)), 'Live Studio process detected');
const server=fixtureServer();
start(server); await once(server,'listening');
let browser;
const screens=[['mission','Mission Control'],['create','Universal Create'],['batch','Batch Studio'],['library','Video Library'],['creative','Creative Library'],['review','Review Studio'],['operations','Operations & Agents'],['jobs/fixture-canal/overview','How canal locks lift boats'],['batch/fixture-b20/validate','Mixed slate / November'],['campaign/fixture-canals/episodes','Inside the waterways']];
const ok = (line) => console.log(`PASS ${line}`);
function raw(path, method='GET', host=new URL(origin).host) {
  return new Promise((resolve,reject)=>{const r=request(`${origin}/`,{path,method,headers:{Host:host}},res=>{res.resume();res.on('end',()=>resolve(res));});r.on('error',reject);r.end();});
}
try {
  for (const path of paths) for(const method of ['GET','HEAD']) assert.equal((await raw(path,method)).statusCode,200);
  for (const path of ['/api/v1/health','/site/','/../serve.mjs','/%2e%2e/serve.mjs','/app.mjs?x=1','/README.md']) assert.equal((await raw(path)).statusCode,404,path);
  assert.equal((await raw('/','POST')).statusCode,405);
  assert.equal((await raw('/','GET','other.invalid')).statusCode,421);
  assert.match((await raw('/')).headers['content-security-policy'],/connect-src 'none'; form-action 'none'/);
  assert.equal((await raw('/')).headers.location,undefined);
  ok('raw HTTP allowlist, methods, host, headers and no redirect');
  browser=await chromium.launch({executablePath,args:['--disable-background-networking','--disable-component-update','--disable-sync']});
  console.log(`Environment: ${process.platform}/${process.arch}, Node ${process.version}, Chromium ${browser.version()}, Playwright ${require('playwright/package.json').version}`);
  const context=await browser.newContext({serviceWorkers:'block',acceptDownloads:false});
  const attempts=[], issues=[];
  await context.route('**/*',r=>{
    const req=r.request(), u=new URL(req.url());
    if(u.origin===origin && paths.includes(u.pathname) && !u.search && ['GET','HEAD'].includes(req.method())) return r.continue();
    attempts.push(`${req.method()} ${req.url()}`); return r.abort();
  });
  await context.routeWebSocket('**/*',ws=>{attempts.push(ws.url());ws.close();});
  await context.addInitScript({path:axePath}); // Browser automation injection, not an app script or CSP exception.
  await context.addInitScript(()=>{ window.fixtureCsp=[]; addEventListener('securitypolicyviolation',e=>window.fixtureCsp.push(e.violatedDirective)); });
  const page=await context.newPage();
  page.on('pageerror',e=>issues.push(e.message));
  page.on('response',r=>{if(r.status()>=400||(r.status()>=300&&r.status()<400))issues.push(`${r.status()} ${r.url()}`);});
  page.on('framenavigated',f=>{if(f.parentFrame()||new URL(f.url()).origin!==origin)issues.push(`Unexpected navigation: ${f.url()}`);});
  page.on('popup',p=>{issues.push('Unexpected popup');p.close();});
  page.on('download',()=>issues.push('Unexpected download'));
  const go=async(route,title)=>{await page.goto(`${origin}/#/${route}`);await page.getByRole('heading',{name:title,exact:true,level:1}).waitFor();};
  const click=name=>page.getByRole('button',{name,exact:true}).click();
  const text=async(value)=>{await page.getByText(value,{exact:false}).first().waitFor();};
  const clean=async()=>{
    assert.deepEqual(issues,[]); assert.deepEqual(attempts,[]);
    assert.deepEqual(await page.evaluate(()=>window.fixtureCsp),[]);
    assert.deepEqual(await context.cookies(),[]);
    assert.deepEqual(await page.evaluate(async()=>[localStorage.length,sessionStorage.length,(await indexedDB.databases()).length,(await caches.keys()).length,(await navigator.serviceWorker.getRegistrations()).length]),[0,0,0,0,0]);
  };
  for(const width of [1440,1024,390,320]) {
    await page.setViewportSize({width,height:960});
    for(const theme of ['dark','light']) for(const [route,title] of screens) {
      await go(route,title);
      if(await page.locator('html').evaluate(e=>e.classList.contains('light'))!==(theme==='light')) await click(theme==='light'?'Light theme':'Dark theme');
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${route} ${width} overflows`);
      await page.evaluate(async()=>{ await Promise.allSettled(document.getAnimations().map(a=>a.finished)); });
      const violations=await page.evaluate(async()=> (await axe.run({runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>[v.id,v.nodes.map(n=>n.target)]));
      assert.deepEqual(violations,[],`${route} ${width} ${theme} axe`);
      if(route==='mission'&&width===1440) {
        const pairs=await page.evaluate(()=>{
          const css=getComputedStyle(document.documentElement);
          function luminance(name){
            const hex=css.getPropertyValue(`--${name}`).trim().slice(1);
            const rgb=(hex.length===3?[...hex].map(v=>v+v):hex.match(/../g)).map(v=>parseInt(v,16)/255);
            return rgb.map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
          }
          return [['text','bg',4.5],['muted','panel',4.5],['accent','raise',4.5],['ink','accent',4.5],['warn','panel',4.5],['focus','bg',3],['focus','raise',3],['edge','panel',3],['edge','raise',3]].map(([a,b,min])=>{
            const values=[luminance(a),luminance(b)].sort((a,b)=>b-a); return [`${a}/${b}`,(values[0]+.05)/(values[1]+.05),min];
          });
        });
        for(const [pair,ratio,min] of pairs)assert(ratio>=min,`${theme} ${pair}: ${ratio} < ${min}`);
        console.log(`Contrast ${theme}: ${pairs.map(([pair,ratio])=>`${pair} ${ratio.toFixed(2)}`).join(', ')}`);
      }
      await clean();
      if((width===1440&&theme==='dark')||(width===390&&theme==='light')||route==='mission') await page.screenshot({path:join(outputPath,`${width}-${theme}-${route.replaceAll('/','-')}.png`),animations:'disabled'});
    }
  }
  ok('10 routes × four widths × two themes: layout, automated axe and fixture-only requests');
  await page.setViewportSize({width:390,height:840});
  await page.emulateMedia({reducedMotion:'reduce',forcedColors:'active'});
  await page.goto(origin);
  await page.getByRole('heading',{name:'Mission Control',level:1}).waitFor();
  await page.keyboard.press('Tab'); assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Skip to content');
  await page.keyboard.press('Enter'); assert.equal(await page.evaluate(()=>document.activeElement.id),'main');
  await page.locator('#open-nav').focus(); await page.keyboard.press('Enter');
  assert.equal(await page.locator('#menu').evaluate(e=>getComputedStyle(e).animationName),'none');
  await page.keyboard.press('Escape'); assert.equal(await page.evaluate(()=>document.activeElement.id),'open-nav');
  await click('Studio menu'); await page.getByRole('dialog').getByRole('link',{name:'Universal Create'}).click();
  await page.getByRole('heading',{name:'Universal Create',level:1}).waitFor();
  assert.equal(await page.evaluate(()=>document.activeElement.tagName),'H1');
  await page.emulateMedia({reducedMotion:null,forcedColors:null});
  ok('mobile keyboard skip, menu Escape/focus return, route focus and reduced motion');
  await page.setViewportSize({width:1440,height:960});
  await page.getByLabel('Target').selectOption('Long-form · 16:9'); await click('Simulate validate'); await text('Blocked: director composition required.');
  await page.getByLabel('Target').selectOption('Shorts · 9:16'); await click('Simulate validate'); await text('Incomplete:');
  await page.getByLabel('Production detail').fill('Open with an illustrated star field.');
  await click('Simulate validate'); await click('Simulate save draft'); await page.getByRole('heading',{name:'A map of the night sky',level:1}).waitFor(); await clean(); ok('create: conditional, invalid, corrected and fixture draft');
  await go('batch/fixture-b20/intake','Mixed slate / November'); await click('Simulate validate batch');
  await page.getByRole('button',{name:'Simulate resolve missing detail'}).first().click();
  await click('Select ready rows'); await text('13 selected'); await click('Simulate interrupted response'); await text('Response interrupted.');
  await click('Recover session receipt'); await text('Blocked by capability drift'); await text('12 simulated submissions');
  await click('Simulate submit selected'); await text('Replayed 13 existing row outcomes'); await text('12 simulated submissions');
  await click('Simulate revalidate unaccepted rows'); await click('Select ready rows'); await click('Simulate submit selected');
  await text('14 simulated submissions'); await clean(); ok('batch: 20 rows, corrected detail, drift, interruption, replay and scoped retry');
  await go('campaign/fixture-canals/episodes','Inside the waterways'); await text('नहर का सफ़र'); await text('Pinned r2');
  await click('Preview draft rebase'); await page.keyboard.press('Escape'); assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Preview draft rebase');
  assert.equal(await page.getByText('Pinned r3.1').count(),0);
  await click('Preview draft rebase'); await click('Simulate rebase'); await text('Pinned r3.1'); await text('Pinned r2'); await clean(); ok('campaign: cancellation, explicit rebase, original pin and Indic text');
  await go('review/script','Review Studio'); await click('Review exact fixture subject'); await click('Simulate grant'); await text('Simulated grant recorded for current revision.');
  await click('Review exact fixture subject'); await click('Simulate newer revision'); assert(await page.getByRole('button',{name:'Simulate grant',exact:true}).isDisabled());
  await click('Cancel'); await click('Review exact fixture subject'); await text('fixture-script-r2'); await click('Simulate grant');
  await go('review/composition','Review Studio'); await page.getByLabel('Storyboard frame').focus(); await page.keyboard.press('Home'); await text('The boat enters the low chamber.');
  await go('library','Video Library'); await page.getByLabel('Technical QA').selectOption('Fail'); await text('Nearest-neighbor map'); assert.equal(await page.getByRole('heading',{name:'How canal locks lift boats',exact:true}).count(),0);
  await page.getByLabel('Technical QA').selectOption('All');
  const mapChoice=page.locator('article').filter({hasText:'Nearest-neighbor map'}).getByRole('checkbox');
  await mapChoice.uncheck(); await click('Preview fixture export plan');
  assert.equal(await page.getByRole('dialog').getByText('Nearest-neighbor map',{exact:false}).count(),0);
  await click('Cancel'); await mapChoice.check(); await click('Preview fixture export plan'); await click('Simulate export selected'); await text('destination conflict'); await clean(); ok('review/export: stale confirmation, scrub, filters and independent receipts');
  await go('jobs/fixture-map/logs','Nearest-neighbor map'); await click('Preview retry and invalidation'); await click('Simulate retry'); await text('01 · Align failed'); await text('02 · Align retry queued'); await text('Retry unavailable');
  await go('operations','Operations & Agents'); await click('Simulate disconnected'); await text('Disconnected'); await click('Simulate unknown state'); await text('Unknown'); await click('Simulate reconnect'); await text('Last observed 14:23');
  await go('creative','Creative Library'); await page.getByRole('button',{name:'Simulate apply to draft'}).first().click(); await text('attached to the in-memory draft');
  await click('Reset'); await page.getByText('Tidal Cut attached', {exact:false}).waitFor({state:'hidden'});
  await go('jobs/fixture-map/logs','Nearest-neighbor map'); await text('01 · Align failed'); assert.equal(await page.getByText('02 · Align retry queued',{exact:false}).count(),0);
  await clean(); ok('recovery, creative selection, reset and empty browser storage');
  const denied=await page.evaluate(async()=>{try{await fetch('/api/v1/health');return false;}catch{return true;}});
  assert(denied); await page.waitForFunction(()=>window.fixtureCsp.includes('connect-src'));
  assert.deepEqual(attempts,[]); ok('CSP blocks deliberate same-origin API attempt before transport');
  await assert.rejects(page.goto('http://fixture-deny.invalid/'),/ERR_FAILED/);
  assert.deepEqual(attempts,['GET http://fixture-deny.invalid/']); ok('external navigation attempt intercepted and aborted before contact (harness negative control)');
} finally { if(browser)await browser.close(); server.closeAllConnections(); await new Promise(resolve=>server.close(resolve)); }
