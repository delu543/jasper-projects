const $ = selector => document.querySelector(selector);
let getSnapshot, save, toast;
const zh = () => document.documentElement.lang === 'zh';
const label = (cn, en) => zh() ? cn : en;
const node = (tag, text, cls='') => {const n=document.createElement(tag); n.textContent=text; n.className=cls; return n;};
const button = (text, action) => {const b=node('button',text,'quiet-button'); b.type='button'; b.onclick=action; return b;};

function field(name, title, value='', choices=null) {
  const wrapper=node('label',''); wrapper.append(node('span',title));
  const input=document.createElement(choices ? 'select' : 'textarea');
  if (choices) for (const [value,text] of choices) {const option=node('option',text);option.value=value;input.append(option);}
  else input.rows=2;
  input.name=name; input.value=value; wrapper.append(input); $('#details-fields').append(wrapper);
}

function edit(title, build, submit) {
  const revision=getSnapshot().revision;
  $('#details-title').textContent=title; $('#details-error').textContent=''; $('#details-fields').replaceChildren();
  build();
  $('#details-form').onsubmit=async event=>{
    event.preventDefault();
    try {await submit(Object.fromEntries(new FormData(event.target)),revision);$('#details-editor').close();toast(label('已保存','Saved'));}
    catch(error){$('#details-error').textContent=error.message;}
  };
  $('#details-editor').showModal();
}

function projectEditor() {
  const project=getSnapshot().project;
  edit(label('项目目标与说明','Project goal and details'),()=>{
    field('projectName',label('名称','Name'),project.name);
    field('summary',label('项目介绍','Summary'),project.summary);
    field('outcome',label('用户最终得到什么','User outcome'),project.outcome);
    field('notes',label('备注与约束','Notes and constraints'),project.notes);
  },(patch,expectedRevision)=>save('/api/project',{patch,expectedRevision}));
}

const issueStatuses=()=>[['unverified',label('待验证','Unverified')],['open',label('待处理','Open')],['doing',label('处理中','In progress')],['resolved',label('已处理','Resolved')]];
function issueEditor(issue=null) {
  edit(label('问题与下一步','Issue and next action'),()=>{
    field('title',label('标题','Title'),issue?.title||'');
    field('impact',label('用户影响','User impact'),issue?.impact||'');
    field('next',label('下一步','Next action'),issue?.next||'');
    field('evidence',label('证据与版本','Evidence and version'),issue?.evidence||'');
    field('status',label('状态','Status'),issue?.status||'unverified',issueStatuses());
  },(patch,expectedRevision)=>save('/api/issue',{patch:{...patch,...(issue?{id:issue.id}:{})},expectedRevision}));
}

function mappingEditor(task) {
  const previous=getSnapshot().taskMappings[task.id];
  edit(label('任务职责与阶段','Task responsibility and phase'),()=>{
    field('phase',label('阶段','Phase'),previous?.phase||'midstream',[
      ['upstream',label('上游','Upstream')],['midstream',label('中游','Midstream')],['downstream',label('下游','Downstream')]]);
    field('role',label('负责的内容','Responsibility'),previous?.role||'');
  },(patch,expectedRevision)=>save('/api/task-mapping',{id:task.id,...patch,expectedRevision}));
}

export function composeRequest(item) {
  const snapshot=getSnapshot();
  const draft={project:snapshot.project, item, version:snapshot.runtime.git,
    instruction:label('核对当前代码和根因，完成事项并报告实际验证及未验证范围。不要把任务活动当成验收。此文本适用于 Codex 或 Claude；复制不代表已发送。',
      'Inspect current code and the root cause. Complete the item and report evidence and remaining validation. Activity is not acceptance. For Codex or Claude; copying does not send it.')};
  $('#request-text').value=JSON.stringify(draft,null,2); $('#request-composer').showModal();
}

export function bindDetails(options) {
  getSnapshot=options.getSnapshot; save=options.api; toast=options.showToast;
  $('#project-settings').onclick=projectEditor;
  $('#add-issue').onclick=()=>issueEditor();
  $('#close-details').onclick=()=>$('#details-editor').close();
  $('#close-composer').onclick=()=>$('#request-composer').close();
  $('#copy-composed').onclick=async()=>{
    try {await navigator.clipboard.writeText($('#request-text').value);toast(label('已复制，请粘贴到目标对话','Copied; paste in the intended chat'));}
    catch {$('#request-error').textContent=label('请手动复制文本','Please copy the text manually');}
  };
  $('#copy-context').onclick=async()=>{
    try {const response=await fetch('/api/context');if(!response.ok)throw new Error('Context unavailable');
      $('#request-text').value=JSON.stringify(await response.json(),null,2);$('#request-composer').showModal();}
    catch(error){toast(error.message);}
  };
}

export function renderDetails(snapshot) {
  $('#project-settings').textContent=label('项目目标','Project goal');
  $('#copy-context').textContent=label('Agent 上下文','Agent context');
  $('#issue-title').textContent=label('问题与下一步','Issues and next actions');
  $('#add-issue').textContent=label('记录问题','Add issue');
  $('#project-outcome').textContent=snapshot.project.outcome||snapshot.project.summary||'';
  $('#board-search').placeholder=label('搜索检查点、问题或任务','Search checkpoints, issues or tasks');
  const query=$('#board-search').value.toLowerCase().trim();
  const issues=snapshot.issues.filter(i=>!query||[i.title,i.impact,i.next].join(' ').toLowerCase().includes(query));
  const list=$('#issue-list');list.replaceChildren();
  if(!issues.length)list.append(node('p',label('没有匹配的问题记录','No matching issue records'),'empty'));
  for(const issue of issues){
    const card=node('article','','paper-panel');
    card.append(node('h3',issue.title),node('small',issueStatuses().find(s=>s[0]===issue.status)?.[1]||issue.status),
      node('p',issue.impact),node('p',label('下一步：','Next: ')+issue.next),node('small',issue.evidence),
      button(label('编辑','Edit'),()=>issueEditor(issue)),button(label('生成 Agent 要求','Draft agent request'),()=>composeRequest(issue)));
    list.append(card);
  }
  if(snapshot.runtime.codex?.stale || snapshot.runtime.codex?.enabled===false)return;
  const tasks=(snapshot.runtime.codex?.tasks||[]).filter(t=>!query||[t.title,t.summary,snapshot.taskMappings[t.id]?.role].join(' ').toLowerCase().includes(query)).slice(0,5);
  const rows=$('#codex-list').querySelectorAll('.task-row');
  tasks.forEach((task,index)=>{
    const row=rows[index];if(!row)return;const mapping=snapshot.taskMappings[task.id];
    row.append(node('small',mapping?`${mapping.phase} · ${mapping.role}`:label('待归类','Unclassified')),
      button(label('关联职责','Map responsibility'),()=>mappingEditor(task)),
      button(label('生成 Agent 要求','Draft agent request'),()=>composeRequest({id:task.id,title:task.title,next:mapping?.role||''})));
  });
}
