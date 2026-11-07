import { test } from 'node:test';
import assert from 'node:assert/strict';
import { KingAI } from '../client.mjs';
import { runSample } from '../examples/saved_profile_quickstart.mjs';
import { previewExpression } from '../observation.mjs';
import { runInNewContext } from 'node:vm';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
const fixture=process.env.KINGAI_TEST_MCP;

test('sample uses the real SDK over fixture stdio', {skip:!fixture}, async()=>{
  const api=new KingAI({mcpExecutable:fixture,timeoutMs:3000});
  try {
    const result=await runSample(api,'sample');
    assert.equal(result.page.url,'https://example.com');
    assert.equal(result.page.title,'Example Domain');
    assert.equal(result.preview.truncated,false);
    const trace=await api.call('fixture_trace');
    assert.equal(trace.filter(x=>x==='browser_start').length,1);
    assert.equal(trace.filter(x=>x==='browser_evaluate').length,1);
    assert.ok(trace.includes('browser_detach'));
    assert.ok(!trace.includes('browser_close'));
  }finally{await api.close();}
});
test('operation/observation groups do not interleave', {skip:!fixture},async()=>{
  const api=new KingAI({mcpExecutable:fixture,timeoutMs:3000});
  try {
    const browser=await api.start();
    await Promise.all([browser.click(undefined,{ref:'e1',observe:true}),browser.click(undefined,{ref:'e1',observe:true})]);
    const trace=(await api.call('fixture_trace')).filter(x=>['browser_click','browser_read','browser_snapshot','tabs_list'].includes(x));
    assert.deepEqual(trace,['browser_click','browser_read','browser_snapshot','tabs_list','browser_click','browser_read','browser_snapshot','tabs_list']);
  }finally{await api.close();}
});
test('actual Node/Java/Go preview scripts execute and bound data',async()=>{
  const expression='({text:"x".repeat(100000),items:Array.from({length:100},(_,i)=>({label:"y".repeat(5000),i}))})';
  const scripts=[previewExpression(expression)];
  const root=process.env.KINGAI_SOURCE_ROOT;
  if(root) for(const relative of ['go/preview-body.js','java/src/main/resources/cn/kingaibrowser/sdk/preview-body.js']) {
    scripts.push('(async () => { const source = await ('+expression+');'+await readFile(join(root,relative),'utf8'));
  }
  for(const script of scripts){
    const result=await runInNewContext(script,{}, {timeout:1000});
    assert.equal(result.truncated,true);
    assert.ok(Buffer.byteLength(JSON.stringify(result),'utf8')<256*1024);
    assert.ok(result.value.text.length<=1000);
  }
});
test('profile CRUD guards and preview errors are preserved', {skip:!fixture},async()=>{
  const api=new KingAI({mcpExecutable:fixture,timeoutMs:3000});
  try {
    const {profileId}=await api.createProfile('crud');
    await api.updateProfile(profileId,{name:'renamed'});
    assert.equal((await api.profile(profileId)).name,'renamed');
    await assert.rejects(api.deleteProfile(profileId),e=>e.code==='CONFIRMATION_REQUIRED');
    const browser=await api.start({profile_id:profileId});
    await assert.rejects(api.updateProfile(profileId,{name:'busy'}),e=>e.code==='SESSION_BUSY');
    const result=await browser.click(undefined,{ref:'e1',observe:true});
    assert.equal(result.observationStatus,'captured');
    await api.call('fixture_fail_next',{code:'RESULT_TOO_LARGE'});
    await assert.rejects(browser.evaluate('document.title'),e=>e.code==='RESULT_TOO_LARGE');
    assert.equal((await api.call('fixture_trace')).filter(x=>x==='browser_evaluate').length,1);
    await browser.close();
    assert.equal((await api.deleteProfile(profileId,{confirm:true})).deleted,true);
  }finally{await api.close();}
});
