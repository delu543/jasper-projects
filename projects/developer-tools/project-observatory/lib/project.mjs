import { randomUUID } from 'node:crypto';

const phases = ['upstream', 'midstream', 'downstream'];
const text = (value, max = 4000) => typeof value === 'string' && value.length <= max;
const required = (value, max) => text(value, max) && Boolean(value.trim());
const fail = message => { throw Object.assign(new Error(message), { statusCode: 400 }); };

export function normalize(config) {
  return {...config, revision: config.revision ?? 1, summary: config.summary ?? '',
    outcome: config.outcome ?? '', notes: config.notes ?? '', issues: config.issues ?? [],
    taskMappings: config.taskMappings ?? {}, integrations: config.integrations ?? {codex:false, github:false},
    milestones: (config.milestones ?? []).map(item => ({...item, next:item.next ?? '',
      environment:item.environment ?? '', reviewLevel:item.reviewLevel ?? 'local'}))};
}

export function validateProject(config) {
  if (!Number.isInteger(config.revision) || config.revision < 1 ||
      !text(config.summary) || !text(config.outcome) || !text(config.notes, 10000)) fail('Invalid project details');
  if (!config.integrations || typeof config.integrations.codex !== 'boolean' || typeof config.integrations.github !== 'boolean') fail('Invalid integrations');
  if (!Array.isArray(config.issues) || config.issues.length > 200) fail('Invalid issues');
  const ids = new Set();
  for (const issue of config.issues) {
    if (!/^[\w-]{1,50}$/.test(issue?.id) || ids.has(issue.id) || !required(issue.title,160) ||
        !text(issue.impact) || !text(issue.next) || !text(issue.evidence) ||
        !['open','doing','resolved','unverified'].includes(issue.status)) fail('Invalid issue');
    ids.add(issue.id);
  }
  if (!config.taskMappings || typeof config.taskMappings !== 'object' || Array.isArray(config.taskMappings) || Object.keys(config.taskMappings).length > 500) fail('Invalid task mappings');
  for (const [id, mapping] of Object.entries(config.taskMappings)) {
    if (!/^[0-9a-f-]{20,64}$/i.test(id) || !mapping || !phases.includes(mapping.phase) || !text(mapping.role,160)) fail('Invalid task mapping');
  }
  for (const item of config.milestones) {
    if (!text(item.owner ?? '',160) || !text(item.next) || !text(item.environment,200) ||
        !['local','real','delivered'].includes(item.reviewLevel)) fail('Invalid milestone review details');
  }
  return config;
}

export function updateProject(config, patch) {
  const next = structuredClone(config);
  for (const key of ['projectName','summary','outcome','notes']) if (key in patch) next[key] = patch[key];
  return next;
}

export function upsertIssue(config, patch) {
  const next = structuredClone(config);
  const index = patch.id ? next.issues.findIndex(item => item.id === patch.id) : -1;
  if (patch.id && index < 0) fail('Unknown issue');
  const old = index < 0 ? {id:`i-${randomUUID().slice(0,8)}`, title:'', impact:'', next:'', evidence:'', status:'unverified'} : next.issues[index];
  const issue = {...old, updatedAt:new Date().toISOString()};
  for (const key of ['title','impact','next','evidence','status']) if (key in patch) issue[key] = patch[key];
  if (index < 0) next.issues.push(issue); else next.issues[index] = issue;
  return next;
}

export function mapTask(config, {id, phase, role}) {
  const next = structuredClone(config);
  next.taskMappings[id] = {phase, role};
  return next;
}

// Convert data, never infer acceptance or inspect another project's files.
export function fromProgress(board, root) {
  if (board?.schemaVersion !== 1 || !board.project || board.project.path !== root ||
      !Array.isArray(board.checkpoints) || !Array.isArray(board.issues) || !board.taskMappings) fail('Legacy board does not belong to this project');
  const statuses = {unreviewed:'planned', planned:'planned', doing:'active', blocked:'blocked',
    local_verified:'accepted', real_verified:'accepted', delivered:'accepted'};
  const milestones = board.checkpoints.map(item => {
    if (!(item.status in statuses)) fail('Unknown legacy checkpoint status');
    return {id:item.id, phase:item.phase, title:item.title, description:'',
      acceptance:item.outcome, owner:item.owner, next:item.next, scope:'code',
      status:statuses[item.status], evidence:item.evidence, environment:item.verifiedEnvironment,
      reviewedCommit:item.verifiedVersion || null, reviewedAt:statuses[item.status] === 'accepted' ? item.updatedAt : null,
      reviewLevel:item.status === 'delivered' ? 'delivered' : item.status === 'real_verified' ? 'real' : 'local',
      updatedAt:item.updatedAt};
  });
  return {schemaVersion:1, revision:1, projectName:board.project.name, language:'zh',
    summary:board.project.summary, outcome:board.project.outcome, notes:board.notes,
    createdAt:board.updatedAt, milestones, issues:board.issues, taskMappings:board.taskMappings,
    integrations:{codex:false, github:false}, reviewLog:[],
    migration:{source:'.progress-observatory/board.json', sourceRevision:board.revision, importedAt:new Date().toISOString()}};
}

export function agentContext(config, runtime, progress) {
  return {project:{name:config.projectName, summary:config.summary, outcome:config.outcome, notes:config.notes},
    revision:config.revision, version:runtime.git, progress, issues:config.issues,
    taskMappings:config.taskMappings, sources:runtime,
    instruction:'Inspect the selected project and current evidence. Activity is not acceptance. Do not send messages or execute project scripts merely by reading this context.'};
}
