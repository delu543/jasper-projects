import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createProject, configPath, validateConfig } from './config.mjs';
import { fromProgress } from './project.mjs';

export async function migrateProgress(root, {apply=false}={}) {
  const source = path.join(root, '.progress-observatory', 'board.json');
  const legacy = JSON.parse(await readFile(source, 'utf8'));
  const candidate = validateConfig(fromProgress(legacy, root));
  for (const item of candidate.milestones) {
    if (/^[a-f0-9]{7,64}$/i.test(item.reviewedCommit || '')) {
      try {
        const {stdout}=await promisify(execFile)('git',['rev-parse','--verify','--end-of-options',`${item.reviewedCommit}^{commit}`],{cwd:root,timeout:3000});
        item.reviewedCommit=stdout.trim();
      } catch { /* Unknown versions remain review-due; never invent a commit. */ }
    }
  }
  if (await stat(configPath(root)).then(()=>true,()=>false)) throw new Error('Canonical project state already exists; original legacy board preserved');
  const preview = {source, destination:configPath(root), applied:false, milestones:candidate.milestones.length,
    issues:candidate.issues.length, taskMappings:Object.keys(candidate.taskMappings).length,
    acceptance:'Existing evidence retained. Counted only when full current commit, clean tree and environment agree.'};
  if (!apply) return preview;
  const result = await createProject(root, {initialConfig:candidate});
  if (!result.created) throw new Error('Canonical state appeared concurrently; legacy board preserved');
  return {...preview, applied:true};
}
