import { execFile } from 'node:child_process';
import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const run=promisify(execFile);
const roots=['package.json','pyproject.toml','Cargo.toml','go.mod','pom.xml','Gemfile','pubspec.yaml','README.md'];
const dirs=['src','app','lib','test','tests','docs','.github/workflows'];
async function command(file,args,cwd,timeout=8000){const {stdout}=await run(file,args,{cwd,timeout,maxBuffer:256*1024});return stdout.trim();}
function hostRepo(remote){
  if(!remote)return null;
  const cleaned=remote.replace(/^git@github\.com:/,'https://github.com/');
  try {const url=new URL(cleaned);if(url.hostname!=='github.com')return null;const match=url.pathname.match(/^\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/);return match?`${match[1]}/${match[2]}`:null;}catch{return null;}
}
export async function collectGit(root,previous={}){
  try{
    const [head,branch,status,subject,committedAt,remote]=await Promise.all([
      command('git',['rev-parse','HEAD'],root),command('git',['branch','--show-current'],root),
      command('git',['status','--porcelain=v1','--untracked-files=normal'],root),
      command('git',['log','-1','--format=%s'],root),command('git',['log','-1','--format=%cI'],root),
      command('git',['remote','get-url','origin'],root).catch(()=>null)
    ]);
    const lines=status?status.split('\n'):[];
    return {head,branch:branch||'(detached)',dirtyCount:lines.length,lastCommit:subject.slice(0,180),committedAt,githubRepo:hostRepo(remote),lastSuccessAt:new Date().toISOString(),stale:false};
  }catch(error){return {...previous,stale:true,error:`Git unavailable (${error.code||'unknown'})`};}
}
export async function collectStructure(root){
  const found=[];
  for(const name of roots){try{if((await stat(path.join(root,name))).isFile())found.push(name);}catch{}}
  for(const name of dirs){try{if((await stat(path.join(root,name))).isDirectory())found.push(name+'/');}catch{}}
  let scripts=[];
  if(found.includes('package.json'))try{const pkg=JSON.parse(await readFile(path.join(root,'package.json'),'utf8'));scripts=Object.keys(pkg.scripts||{}).filter(x=>/^(test|lint|typecheck|build|check|e2e|verify)(:|$)/.test(x)).slice(0,16);}catch{}
  const languages=found.filter(x=>['package.json','pyproject.toml','Cargo.toml','go.mod','pom.xml','Gemfile','pubspec.yaml'].includes(x));
  return {found,languages,scripts,lastSuccessAt:new Date().toISOString(),stale:false};
}
export async function collectGithub(root,repo,previous={}){
  if(!repo)return {stale:true,error:'No GitHub origin found'};
  try{
    const [remoteHead,runsJson]=await Promise.all([
      command('gh',['api',`repos/${repo}/commits?per_page=1`,'--jq','.[0].sha'],root,9000),
      command('gh',['run','list','--repo',repo,'--limit','4','--json','name,status,conclusion,headSha,createdAt'],root,9000)
    ]);
    return {repo,remoteHead,runs:JSON.parse(runsJson),lastSuccessAt:new Date().toISOString(),stale:false};
  }catch(error){return {...previous,repo,stale:true,error:`GitHub unavailable (${error.code||'unknown'})`};}
}
export async function collectCodex(root,previous={}){
  const script=fileURLToPath(new URL('./codex_scan.py',import.meta.url));
  try{
    const data=await new Promise((resolve,reject)=>{
      const child=spawn(process.platform==='win32'?'python':'python3',[script,root],{stdio:['ignore','pipe','ignore']});let output='';
      const timer=setTimeout(()=>{child.kill();reject(new Error('timeout'));},8000);
      child.stdout.on('data',c=>{output+=c;if(output.length>256*1024)child.kill();});
      child.on('error',e=>{clearTimeout(timer);reject(e);});
      child.on('close',code=>{clearTimeout(timer);try{if(code)throw new Error('scanner');resolve(JSON.parse(output));}catch(e){reject(e);}});
    });
    return {...data,lastSuccessAt:new Date().toISOString(),stale:false};
  }catch{return {...previous,stale:true,error:'Codex index unavailable; project data was retained'};}
}
export async function collectSnapshot(root,config,previous={},mode='full'){
  const [git,structure]=await Promise.all([collectGit(root,previous.git),collectStructure(root)]);
  const github=config.integrations.github && mode==='full'?await collectGithub(root,git.githubRepo,previous.github):
    config.integrations.github?previous.github||{stale:true,error:'Waiting for remote refresh'}:{enabled:false};
  const codex=config.integrations.codex?await collectCodex(root,previous.codex):{enabled:false};
  return {schemaVersion:1,collectedAt:new Date().toISOString(),git,structure,github,codex};
}
