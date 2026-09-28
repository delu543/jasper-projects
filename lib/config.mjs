import { randomUUID } from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { appendFile, mkdir, readFile, rename, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';

const directory = '.project-observatory';
const run=promisify(execFile);
export const phases = ['upstream', 'midstream', 'downstream'];
const catalog = [
  ['scope','upstream','Scope and success criteria','目标与验收范围','Decide what users need and what will prove it works.','明确用户需求，以及怎样证明它可用。','decision'],
  ['design','upstream','Architecture and risks','方案与风险','Agree on responsibilities, dependencies and risks.','明确职责、依赖和主要风险。','decision'],
  ['build','midstream','Core implementation','核心功能开发','Implement the smallest complete user path.','完成最小但完整的用户路径。','code'],
  ['integrate','midstream','Integration and state','集成与状态','Connect modules and verify state ownership.','接通模块并核对状态归属。','code'],
  ['regression','downstream','Development regression','开发回归验收','Run tests that cover the changed behavior and failure.','运行覆盖改动和失败根因的测试。','code'],
  ['experience','downstream','Real user journey','真实使用体验','Try the complete path with realistic input.','用真实规模输入体验完整流程。','code'],
  ['release','downstream','Release readiness','交付与发布准备','Check environment, rollout and recovery.','核对环境、发布和恢复路径。','code'],
  ['operate','downstream','Operation and learning','运行观察与复盘','Observe the delivered version and capture follow up work.','观察交付版本并记录后续问题。','decision']
];
export const configPath = (root) => path.join(root, directory, 'project.json');
export const runtimePath = (root) => path.join(root, directory, 'runtime.json');
export const defaultMilestones = (language='en') => catalog.map(([id,phase,en,zh,enDescription,zhDescription,scope]) => ({
  id, phase, title:language==='zh'?zh:en, description:language==='zh'?zhDescription:enDescription,
  acceptance:'', status:'planned', scope, evidence:[], owner:'', reviewedAt:null, reviewedCommit:null, updatedAt:null
}));
export function validateConfig(config) {
  if (config?.schemaVersion !== 1 || typeof config.projectName !== 'string' || config.projectName.length > 120 || !Array.isArray(config.milestones)) throw new Error('Invalid project configuration');
  if (config.milestones.length > 80) throw new Error('Too many milestones');
  const ids = new Set();
  for (const item of config.milestones) {
    if (!/^[a-zA-Z0-9_-]{1,50}$/.test(item.id) || ids.has(item.id) || !phases.includes(item.phase) || !['planned','active','ready','accepted','blocked'].includes(item.status) || !['code','decision'].includes(item.scope)) throw new Error(`Invalid milestone ${item.id}`);
    if (typeof item.title !== 'string' || item.title.length > 140 || typeof item.description !== 'string' || item.description.length > 1000 || typeof item.acceptance !== 'string' || item.acceptance.length > 1200 || !Array.isArray(item.evidence) || item.evidence.length > 12 || item.evidence.some(x=>typeof x!=='string'||x.length>500)) throw new Error(`Invalid milestone content ${item.id}`);
    ids.add(item.id);
  }
  return config;
}
export async function atomicJson(filename, value) {
  await mkdir(path.dirname(filename), {recursive:true});
  const temp = `${filename}.${process.pid}.${randomUUID()}.tmp`;
  await writeFile(temp, JSON.stringify(value,null,2)+'\n', {mode:0o600});
  await rename(temp,filename);
}
export async function readConfig(root) { return validateConfig(JSON.parse(await readFile(configPath(root),'utf8'))); }
export async function createProject(root, {language='en',name}={}) {
  const existing=await stat(configPath(root)).then(()=>true,()=>false);
  if(existing) return {created:false,config:await readConfig(root)};
  let packageName;
  try {const pkg=JSON.parse(await readFile(path.join(root,'package.json'),'utf8'));packageName=pkg.displayName||pkg.name;} catch {}
  const config={schemaVersion:1,projectName:String(name||packageName||path.basename(root)).slice(0,120),language:language==='zh'?'zh':'en',createdAt:new Date().toISOString(),milestones:defaultMilestones(language),reviewLog:[],integrations:{codex:false,github:false}};
  await atomicJson(configPath(root),config);
  // The local Git exclude avoids making a fresh checkout dirty during init.
  let ignore;
  try {const {stdout}=await run('git',['rev-parse','--git-path','info/exclude'],{cwd:root,timeout:3000});ignore=path.resolve(root,stdout.trim());}
  catch {ignore=path.join(root,'.gitignore');}
  let existingIgnore='';try{existingIgnore=await readFile(ignore,'utf8');}catch{}
  if(!existingIgnore.split(/\r?\n/).includes('.project-observatory/'))
    await appendFile(ignore,`${existingIgnore&&!existingIgnore.endsWith('\n')?'\n':''}.project-observatory/\n`);
  return {created:true,config};
}
export function milestoneProgress(config, currentHead, dirtyCount=0) {
  const unique=new Map(config.milestones.map(x=>[x.id,x]));
  const items=[...unique.values()].map(item=>{
    const stale=item.status==='accepted'&&item.scope==='code'&&(!currentHead||item.reviewedCommit!==currentHead||dirtyCount>0);
    const accepted=item.status==='accepted'&&!stale&&item.evidence.length>0&&Boolean(item.reviewedAt);
    return {...item,effectiveStatus:stale?'needs_review':item.status,accepted,stale};
  });
  return {done:items.filter(x=>x.accepted).length,total:items.length,items,
    phases:phases.map(id=>{const part=items.filter(x=>x.phase===id);return{id,done:part.filter(x=>x.accepted).length,total:part.length};})};
}
export function updateMilestone(config, id, patch, runtime) {
  const index=config.milestones.findIndex(x=>x.id===id);
  if(index<0) throw Object.assign(new Error('Unknown milestone'),{statusCode:404});
  const old=config.milestones[index];
  const item={...old};
  for(const key of ['title','description','acceptance','owner','status']) if(key in patch) item[key]=patch[key];
  if('evidence' in patch)item.evidence=patch.evidence;
  if(item.status==='accepted') {
    if(!item.evidence.length) throw Object.assign(new Error('Acceptance needs evidence'),{statusCode:400});
    if(item.scope==='code'&&(!runtime.git?.head||runtime.git?.dirtyCount>0||runtime.git?.stale)) throw Object.assign(new Error('Code acceptance needs a clean Git commit'),{statusCode:409});
    item.reviewedAt=new Date().toISOString();item.reviewedCommit=item.scope==='code'?runtime.git.head:null;
  } else if(old.status==='accepted'&&item.status!=='accepted') {item.reviewedAt=null;item.reviewedCommit=null;}
  item.updatedAt=new Date().toISOString();
  const next=structuredClone(config);next.milestones[index]=item;
  next.reviewLog=[...(next.reviewLog||[]),{id,from:old.status,to:item.status,at:item.updatedAt,commit:item.reviewedCommit}].slice(-100);
  return validateConfig(next);
}

export function addMilestone(config, patch) {
  const title=String(patch.title||'').trim();
  const phase=String(patch.phase||'');
  if(!title||title.length>140||!phases.includes(phase))throw Object.assign(new Error('A title and valid phase are required'),{statusCode:400});
  const now=new Date().toISOString();
  const item={id:`m-${randomUUID().slice(0,8)}`,phase,title,description:String(patch.description||'').slice(0,1000),acceptance:String(patch.acceptance||'').slice(0,1200),status:'planned',scope:patch.scope==='decision'?'decision':'code',evidence:[],owner:'',reviewedAt:null,reviewedCommit:null,updatedAt:now};
  const next=structuredClone(config);next.milestones.push(item);return validateConfig(next);
}
