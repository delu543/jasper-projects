import { open, unlink } from 'node:fs/promises';
import { atomicJson, configPath, readConfig, validateConfig } from './config.mjs';

// One writer across tabs/servers, plus a revision lease for stale editors.
export async function saveConfig(root, candidate, expectedRevision) {
  const filename = configPath(root);
  let lock;
  try { lock = await open(filename + '.lock', 'wx', 0o600); }
  catch (error) {
    if (error.code === 'EEXIST') throw Object.assign(new Error('Project state is being saved; refresh before retrying'), {statusCode:409});
    throw error;
  }
  try {
    const current = await readConfig(root);
    if (!Number.isInteger(expectedRevision) || current.revision !== expectedRevision)
      throw Object.assign(new Error('Project changed since this editor opened; refresh and review your changes'), {statusCode:409});
    const next = validateConfig({...candidate, revision:current.revision+1, updatedAt:new Date().toISOString()});
    await atomicJson(filename, next);
    return next;
  } finally { await lock.close(); await unlink(filename + '.lock'); }
}
