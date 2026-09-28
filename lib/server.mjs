import http from 'node:http';
import { randomBytes } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { addMilestone, atomicJson, configPath, milestoneProgress, readConfig, updateMilestone, validateConfig } from './config.mjs';
import { collectGit, collectSnapshot } from './collect.mjs';
const publicDir=fileURLToPath(new URL('../public/',import.meta.url));
const assets={'/':['index.html','text/html; charset=utf-8'],'/app.js':['app.js','text/javascript; charset=utf-8'],'/style.css':['style.css','text/css; charset=utf-8'],'/favicon.svg':['favicon.svg','image/svg+xml']};
const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"};
function json(response,code,value){const body=JSON.stringify(value);response.writeHead(code,{...headers,'Content-Type':'application/json; charset=utf-8'});response.end(body);}
async function bodyJson(request){let text='';for await(const chunk of request){text+=chunk;if(text.length>32*1024)throw Object.assign(new Error('Request too large'),{statusCode:413});}try{return JSON.parse(text);}catch{throw Object.assign(new Error('Invalid JSON'),{statusCode:400});}}
export async function startServer(root,{port=4187,logger=console.log}={}){
  let config=await readConfig(root);
  let runtime=await collectSnapshot(root,config,{},'full');
  const token=randomBytes(24).toString('hex');
  const clients=new Set();let timers=[],refreshing=false,queuedFull=false,mutation=Promise.resolve();
  const snapshot=()=>({schemaVersion:1,project:{name:config.projectName,language:config.language,createdAt:config.createdAt},milestones:milestoneProgress(config,runtime.git?.head,runtime.git?.dirtyCount),runtime,integrations:config.integrations,csrf:token});
  const broadcast=()=>{const message=`event: update\ndata: ${JSON.stringify({at:new Date().toISOString()})}\n\n`;for(const client of clients)if(!client.write(message)){client.destroy();clients.delete(client);}};
  async function refresh(mode='local'){
    if(refreshing){if(mode==='full')queuedFull=true;return;}
    refreshing=true;
    try{runtime=await collectSnapshot(root,config,runtime,mode);broadcast();}
    catch{runtime={...runtime,collectedAt:new Date().toISOString(),collectorError:'Collection failed; previous values retained'};broadcast();}
    finally{refreshing=false;if(queuedFull&&clients.size){queuedFull=false;void refresh('full');}}
  }
  function startTimers(){if(timers.length)return;void refresh('full');timers=[setInterval(()=>void refresh('local'),10000),setInterval(()=>void refresh('full'),60000),setInterval(()=>{for(const client of clients)client.write(': keep-alive\n\n');},20000)];}
  function stopTimers(){timers.forEach(clearInterval);timers=[];}
  const server=http.createServer(async(request,response)=>{
    const address=server.address();const actualPort=address?.port;
    const host=request.headers.host;
    if(host!==`127.0.0.1:${actualPort}`&&host!==`localhost:${actualPort}`){json(response,403,{error:'Invalid host'});return;}
    let pathname;try{pathname=new URL(request.url||'/',`http://${host}`).pathname;}catch{json(response,400,{error:'Invalid URL'});return;}
    if(request.method==='GET'&&pathname==='/api/events'){
      if(clients.size>=16){json(response,503,{error:'Too many viewers'});return;}
      response.writeHead(200,{...headers,'Content-Type':'text/event-stream; charset=utf-8','Connection':'keep-alive','X-Accel-Buffering':'no'});
      response.write('retry: 2500\n\n');clients.add(response);startTimers();response.on('close',()=>{clients.delete(response);if(!clients.size)stopTimers();});return;
    }
    if(request.method==='GET'&&pathname==='/api/snapshot'){json(response,200,snapshot());return;}
    if(request.method==='POST'&&['/api/milestone','/api/milestones','/api/integrations'].includes(pathname)){
      const origin=request.headers.origin;
      if(origin!==`http://127.0.0.1:${actualPort}`&&origin!==`http://localhost:${actualPort}`){json(response,403,{error:'Invalid origin'});return;}
      if(request.headers['x-panel-token']!==token||!String(request.headers['content-type']||'').startsWith('application/json')){json(response,403,{error:'Invalid local token'});return;}
      try{
        const payload=await bodyJson(request);
        const update=async()=>{
          if(pathname==='/api/milestone'){
            const patch=payload.patch||{};
            if(patch.status==='accepted'&&config.milestones.find(x=>x.id===payload.id)?.scope==='code'){
              const fresh=await collectGit(root,runtime.git);runtime={...runtime,git:fresh,collectedAt:new Date().toISOString()};
              if(!payload.expectedHead||payload.expectedHead!==fresh.head)throw Object.assign(new Error('Git changed since this checkpoint was opened; review the current version'),{statusCode:409});
            }
            config=updateMilestone(config,payload.id,patch,runtime);
          }
          else if(pathname==='/api/milestones')config=addMilestone(config,payload);
          else {if(typeof payload.codex!=='boolean'||typeof payload.github!=='boolean')throw Object.assign(new Error('Invalid integration flags'),{statusCode:400});config=validateConfig({...config,integrations:{codex:payload.codex,github:payload.github}});}
          await atomicJson(configPath(root),config);if(pathname==='/api/integrations')runtime=await collectSnapshot(root,config,runtime,'full');broadcast();return snapshot();
        };
        const action=mutation.then(update);mutation=action.catch(()=>{});json(response,200,await action);
      }catch(error){json(response,error.statusCode||500,{error:error.statusCode?error.message:'Unable to save project state'});}return;
    }
    if(request.method==='GET'&&pathname in assets){try{const [filename,mime]=assets[pathname];const data=await readFile(path.join(publicDir,filename));response.writeHead(200,{...headers,'Content-Type':mime,'Content-Length':data.length});response.end(data);}catch{json(response,500,{error:'Asset unavailable'});}return;}
    json(response,404,{error:'Not found'});
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',()=>{server.off('error',reject);resolve();});});
  const address=server.address();logger(`Project Observatory: http://127.0.0.1:${address.port}`);
  const close=async()=>{stopTimers();for(const client of clients)client.end();clients.clear();await new Promise(resolve=>server.close(resolve));};
  return {server,address,close,getSnapshot:snapshot};
}
