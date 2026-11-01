#!/usr/bin/env node
import path from 'node:path';
import { realpath } from 'node:fs/promises';
import { createProject, readConfig } from '../lib/config.mjs';
import { startServer } from '../lib/server.mjs';

function option(args,name,fallback) {const i=args.indexOf(`--${name}`);return i>=0?args[i+1]??fallback:fallback;}
const [action='help',...args]=process.argv.slice(2);
if(action==='help'||args.includes('--help')){
  process.stdout.write(`Project Observatory\n\n  project-observatory init --project . [--lang zh|en] [--name NAME]\n  project-observatory serve --project . [--port 4187]\n  project-observatory status --project .\n\nRun init separately inside each project. Data stays in that project's .project-observatory directory.\n`);process.exit(0);
}
try {
  const root=await realpath(path.resolve(option(args,'project','.')));
  if(action==='init'){
    const result=await createProject(root,{language:option(args,'lang','en'),name:option(args,'name',null)});
    process.stdout.write(`${result.created?'Created':'Already initialized'}: ${path.join(root,'.project-observatory','project.json')}\n`);
    process.stdout.write('Local data is ignored by this checkout\'s local Git exclude (or .gitignore outside Git).\n');
  } else if(action==='serve'){
    await readConfig(root);
    await startServer(root,{port:Number(option(args,'port',4187))});
  } else if(action==='status'){
    const config=await readConfig(root);process.stdout.write(`${config.projectName}: ${config.milestones.length} milestones\n`);
  } else throw new Error(`Unknown command: ${action}`);
} catch(error) {process.stderr.write(`Project Observatory: ${error.message}\n`);process.exitCode=1;}
