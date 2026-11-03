import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createProject, readConfig, updateMilestone, milestoneProgress, configPath } from '../lib/config.mjs';
import { collectSnapshot } from '../lib/collect.mjs';
import { startServer } from '../lib/server.mjs';
const run=promisify(execFile);
async function fixture(name){const root=await mkdtemp(path.join(tmpdir(),`observatory-${name}-`));await run('git',['init','-b','main'],{cwd:root});await writeFile(path.join(root,'README.md'),`# ${name}\n`);await run('git',['add','README.md'],{cwd:root});await run('git',['-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','start'],{cwd:root});return root;}

test('two projects keep independent local state and ignored data',async()=>{
 const a=await fixture('alpha'),b=await fixture('beta');
 await createProject(a,{name:'Alpha',language:'en'});await createProject(b,{name:'Beta',language:'zh'});
 const configA=await readConfig(a),configB=await readConfig(b);
 const runtimeA=await collectSnapshot(a,configA);const changed=updateMilestone(configA,'scope',{status:'accepted',evidence:['Product review 2026-09-29']},runtimeA);
 await writeFile(configPath(a),JSON.stringify(changed));
 assert.equal(milestoneProgress(await readConfig(a),runtimeA.git.head).done,1);
 assert.equal(milestoneProgress(await readConfig(b),runtimeA.git.head).done,0);
 assert.equal(configB.projectName,'Beta');assert.match(await readFile(path.join(a,'.git','info','exclude'),'utf8'),/\.project-observatory\//);
 const {stdout}=await run('git',['status','--short'],{cwd:a});assert.equal(stdout.trim(), '');
});

test('code acceptance requires clean current commit and becomes review due after code changes',async()=>{
 const root=await fixture('code');await createProject(root);
 const config=await readConfig(root);let runtime=await collectSnapshot(root,config);
 assert.throws(()=>updateMilestone(config,'build',{status:'accepted'},runtime),/evidence/);
 const accepted=updateMilestone(config,'build',{status:'accepted',evidence:['node --test exit 0'],environment:'synthetic Node fixture'},runtime);
 assert.equal(milestoneProgress(accepted,runtime.git.head,0).done,1);
 await writeFile(path.join(root,'README.md'),'# changed\n');runtime=await collectSnapshot(root,accepted);
 assert.equal(milestoneProgress(accepted,runtime.git.head,runtime.git.dirtyCount).items.find(x=>x.id==='build').effectiveStatus,'needs_review');
 assert.throws(()=>updateMilestone(config,'build',{status:'accepted',evidence:['manual claim']},runtime),/clean Git/);
 await run('git',['add','README.md'],{cwd:root});await run('git',['-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','change'],{cwd:root});
 runtime=await collectSnapshot(root,accepted);assert.equal(milestoneProgress(accepted,runtime.git.head,0).done,0);
});

test('local API validates origin/token and persists only in selected project',async()=>{
 const root=await fixture('server'),other=await fixture('other');await createProject(root);await createProject(other);
 const app=await startServer(root,{port:0,logger:()=>{}});const url=`http://127.0.0.1:${app.address.port}`;
 try{
  const snap=await (await fetch(url+'/api/snapshot')).json();assert.equal(snap.project.name,path.basename(root));
  const payload={expectedRevision:snap.revision,id:'scope',patch:{status:'accepted',evidence:['Decision note']}};
  const denied=await fetch(url+'/api/milestone',{method:'POST',headers:{'Content-Type':'application/json','Origin':url},body:JSON.stringify(payload)});assert.equal(denied.status,403);
  const foreign=await fetch(url+'/api/milestone',{method:'POST',headers:{'Content-Type':'application/json','Origin':'https://other.example','X-Panel-Token':snap.csrf},body:JSON.stringify(payload)});assert.equal(foreign.status,403);
  const accepted=await fetch(url+'/api/milestone',{method:'POST',headers:{'Content-Type':'application/json','Origin':url,'X-Panel-Token':snap.csrf},body:JSON.stringify(payload)});assert.equal(accepted.status,200);
  assert.equal((await accepted.json()).milestones.done,1);
  assert.equal((await readConfig(root)).milestones.find(x=>x.id==='scope').status,'accepted');
  assert.equal((await readConfig(other)).milestones.find(x=>x.id==='scope').status,'planned');
  const codePayload={id:'build',patch:{status:'accepted',evidence:['node --test exit 0'],environment:'synthetic Node fixture'}};
  const missingHead=await fetch(url+'/api/milestone',{method:'POST',headers:{'Content-Type':'application/json','Origin':url,'X-Panel-Token':snap.csrf},body:JSON.stringify(codePayload)});assert.equal(missingHead.status,409);
  const expectedHead=snap.runtime.git.head;
  await writeFile(path.join(root,'README.md'),'# server changed\n');
  await run('git',['add','README.md'],{cwd:root});await run('git',['-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','changed'],{cwd:root});
  const staleHead=await fetch(url+'/api/milestone',{method:'POST',headers:{'Content-Type':'application/json','Origin':url,'X-Panel-Token':snap.csrf},body:JSON.stringify({...codePayload,expectedHead})});assert.equal(staleHead.status,409);
  const added=await fetch(url+'/api/milestones',{method:'POST',headers:{'Content-Type':'application/json','Origin':url,'X-Panel-Token':snap.csrf},body:JSON.stringify({expectedRevision:2,phase:'midstream',title:'One more real checkpoint'})});assert.equal(added.status,200);assert.equal((await added.json()).milestones.total,9);
 }finally{await app.close();}
});
