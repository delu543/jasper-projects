"""Optional, read-only Codex adapter. Emits only project-scoped task summaries."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

SECRET = re.compile(r'(?i)(?:bearer\s+\S+|sk-[\w-]{12,}|(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+)')
def clean(value, limit=240):
    value=SECRET.sub('[redacted]',value or '')
    value=re.sub(r'https?://\S+','[link]',value)
    return re.sub(r'\s+',' ',value).strip()[:limit]
def summary(log, sessions):
    try:
        target=Path(log).resolve()
        if not target.is_relative_to(sessions):return ''
        with target.open('rb') as f:
            f.seek(max(0,target.stat().st_size-128*1024))
            if f.tell():f.readline()
            lines=f.read(128*1024).splitlines()
        for line in reversed(lines):
            try:record=json.loads(line)
            except (ValueError,UnicodeDecodeError):continue
            payload=record.get('payload',{})
            if record.get('type')!='response_item' or payload.get('type')!='message' or payload.get('role')!='assistant':continue
            text=' '.join(x.get('text','') for x in payload.get('content',[]) if x.get('type') in ('text','output_text'))
            if text:return clean(text)
    except (OSError,ValueError):pass
    return ''
def main(root,codex_home):
    db=codex_home/'state_5.sqlite'
    if not db.exists():raise FileNotFoundError('index unavailable')
    sessions=(codex_home/'sessions').resolve();tasks=[]
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=2) as con:
        con.row_factory=sqlite3.Row
        con.execute('PRAGMA query_only=ON')
        # Match current checkout only. A title or summary is never used to claim project ownership.
        rows=con.execute("SELECT id,coalesce(nullif(name,''),title) title,cwd,rollout_path,updated_at FROM threads WHERE archived=0 AND source IN ('vscode','cli','exec') AND (cwd=? OR substr(cwd,1,?)=?) ORDER BY updated_at DESC LIMIT 30",(str(root),len(str(root))+1,str(root)+'/')).fetchall()
        for row in rows:
            tasks.append({'id':row['id'],'title':clean(row['title'],90) or 'Untitled task',
                          'updatedAt':dt.datetime.fromtimestamp(row['updated_at'],dt.timezone.utc).isoformat(),
                          'summary':summary(row['rollout_path'],sessions)})
    return {'tasks':tasks,'scope':str(root),'source':'local Codex index and bounded assistant messages'}
if __name__=='__main__':
    try:
        root=Path(sys.argv[1]).resolve()
        home=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex'))).resolve()
        print(json.dumps(main(root,home),ensure_ascii=False))
    except (OSError,sqlite3.Error,ValueError) as error:
        print(json.dumps({'error':type(error).__name__}))
        sys.exit(1)
