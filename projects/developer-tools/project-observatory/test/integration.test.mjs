import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createProject, readConfig, milestoneProgress, configPath, updateMilestone } from '../lib/config.mjs';
import { saveConfig } from '../lib/storage.mjs';
import { migrateProgress } from '../lib/migrate.mjs';
import { startServer } from '../lib/server.mjs';
const run=promisify(execFile);
async function fixture(){
  const root=await mkdtemp(path.join(tmpdir(),'observatory-integrated-'));
  await run('git',['init','-b','main'],{cwd:root});await writeFile(path.join(root,'README.md'),'# Fixture\n');
  await run('git',['add','README.md'],{cwd:root});await run('git',['-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture'],{cwd:root});
  return root;
}

test('legacy import previews without writes and preserves outcomes, issues, mappings and evidence',async()=>{
  const root=await fixture();const {stdout}=await run('git',['rev-parse','HEAD'],{cwd:root});const head=stdout.trim();
  const folder=path.join(root,'.progress-observatory');await mkdir(folder);
  const legacy={schemaVersion:1,revision:7,updatedAt:'2026-09-29T00:00:00Z',project:{name:'Original',path:root,summary:'Summary',outcome:'User outcome'},notes:'Keep this',
    checkpoints:[{id:'D01',phase:'downstream',title:'Regression',outcome:'x'.repeat(2000),status:'real_verified',owner:'Reviewer',next:'Check delivery',evidence:['report'],verifiedVersion:head.slice(0,9),verifiedEnvironment:'synthetic fixture',updatedAt:'2026-09-29T00:00:00Z'}],
    issues:[{id:'I01',title:'Existing issue',impact:'Impact',next:'Investigate',evidence:'repro',status:'open'}],taskMappings:{'01234567-0123-0123-0123-012345678901':{phase:'midstream',role:'Implementation'}}};
  const file=path.join(folder,'board.json');const raw=JSON.stringify(legacy);await writeFile(file,raw);
  const preview=await migrateProgress(root);assert.equal(preview.applied,false);await assert.rejects(readFile(configPath(root)),/ENOENT/);
  await migrateProgress(root,{apply:true});const config=await readConfig(root);
  assert.equal(config.outcome,'User outcome');assert.equal(config.milestones[0].acceptance.length,2000);
  assert.equal(config.milestones[0].reviewLevel,'real');assert.equal(config.milestones[0].reviewedCommit,head);
  assert.equal(config.issues[0].next,'Investigate');assert.deepEqual(config.taskMappings,legacy.taskMappings);
  assert.equal(milestoneProgress(config,head).done,1);assert.equal(milestoneProgress(config,head,0,true).done,0);
  assert.equal(await readFile(file,'utf8'),raw);await assert.rejects(migrateProgress(root,{apply:true}),/already exists/);
  assert.equal(await readFile(file,'utf8'),raw);
});

test('a stale tab or another server cannot overwrite the latest project details',async()=>{
  const root=await fixture();await createProject(root);const first=await readConfig(root);
  await saveConfig(root,{...first,outcome:'Latest saved goal'},first.revision);
  await assert.rejects(saveConfig(root,{...first,outcome:'Old tab'},first.revision),error=>error.statusCode===409);
  assert.equal((await readConfig(root)).outcome,'Latest saved goal');
});

test('unified API persists project, issues and mappings; agent context excludes edit token',async()=>{
  const root=await fixture();await createProject(root);const app=await startServer(root,{port:0,logger:()=>{}});
  const url=`http://127.0.0.1:${app.address.port}`;
  try {
    let state=await (await fetch(url+'/api/snapshot')).json();
    async function post(endpoint,payload,expected=200){
      const response=await fetch(url+endpoint,{method:'POST',headers:{Origin:url,'Content-Type':'application/json','X-Panel-Token':state.csrf},body:JSON.stringify({expectedRevision:state.revision,...payload})});
      assert.equal(response.status,expected);const result=await response.json();if(expected===200)state=result;return result;
    }
    await post('/api/project',{patch:{outcome:'One user result',summary:'Selected project'}});
    await post('/api/issue',{patch:{title:'Root cause',impact:'Blocks use',evidence:'case',next:'Fix state',status:'open'}});
    await post('/api/task-mapping',{id:'01234567-0123-0123-0123-012345678901',phase:'midstream',role:'Fix the root cause'});
    await post('/api/project',{expectedRevision:1,patch:{outcome:'Old edit'}},409);
    const context=await (await fetch(url+'/api/context')).json();assert.equal(context.project.outcome,'One user result');
    assert.equal(context.issues[0].next,'Fix state');assert.equal(context.csrf,undefined);assert.equal(context.progress.total,8);
    assert.equal((await fetch(url+'/project-ui.js')).status,200);
    const git=state.runtime.git;
    await post('/api/milestone',{id:'build',expectedHead:git.head,patch:{status:'accepted',evidence:['case']}},400);
    await post('/api/milestone',{id:'build',expectedHead:git.head,patch:{status:'accepted',evidence:['case'],environment:'local fixture',reviewLevel:'local'}});
    assert.equal(state.milestones.done,1);
    assert.equal((await readConfig(root)).projectName,path.basename(root));
  } finally {await app.close();}
});

test('old board evidence without environment remains visible but is not current acceptance',async()=>{
  const root=await fixture();await createProject(root);const config=await readConfig(root);
  const item=config.milestones.find(i=>i.id==='build');Object.assign(item,{status:'accepted',reviewedAt:new Date().toISOString(),reviewedCommit:'a'.repeat(40),evidence:['old result']});
  assert.equal(milestoneProgress(config,'a'.repeat(40)).done,0);
  assert.throws(()=>updateMilestone(config,'build',{status:'accepted',evidence:['result']},{git:{head:'a'.repeat(40),dirtyCount:0}}),/environment/);
});
