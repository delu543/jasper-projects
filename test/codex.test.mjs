import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, realpath, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
const run=promisify(execFile);
test('optional Codex adapter scopes rows to one project and redacts task text',async t=>{
 let python='python3';try{await run(python,['--version']);}catch{t.skip('Python is optional');return;}
 const root=await realpath(await mkdtemp(path.join(tmpdir(),'observer-codex-')));const project=path.join(root,'project');const other=path.join(root,'other');const home=path.join(root,'codex');
 await mkdir(project);await mkdir(other);await mkdir(path.join(home,'sessions'),{recursive:true});
 const log=path.join(home,'sessions','task.jsonl');await writeFile(log,JSON.stringify({type:'response_item',payload:{type:'message',role:'assistant',content:[{type:'output_text',text:'Working on feature token=private-value'}]}})+'\n');
 const setup=`import sqlite3,sys\nc=sqlite3.connect(sys.argv[1]);c.execute('create table threads(id text,name text,title text,cwd text,rollout_path text,updated_at integer,archived integer,source text)');c.executemany('insert into threads values(?,?,?,?,?,?,?,?)',[("current","Current task","",sys.argv[2],sys.argv[4],1000000000,0,"vscode"),("other","Other project","",sys.argv[3],sys.argv[4],1000000000,0,"vscode"),("agent","Internal agent","",sys.argv[2],sys.argv[4],1000000000,0,"{\\"subagent\\":{}}")]);c.commit()`;
 await run(python,['-c',setup,path.join(home,'state_5.sqlite'),project,other,log]);
 const {stdout}=await run(python,['lib/codex_scan.py',project],{cwd:fileURLToPath(new URL('..',import.meta.url)),env:{...process.env,CODEX_HOME:home}});
 const data=JSON.parse(stdout);assert.equal(data.tasks.length,1);assert.equal(data.tasks[0].id,'current');assert.match(data.tasks[0].summary,/\[redacted\]/);assert.doesNotMatch(stdout,/private-value|Other project|Internal agent/);
});
