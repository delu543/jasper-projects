"""Task discovery shared by the CLI and agents; no runtime or account access."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def capabilities():
    return json.loads((ROOT / 'docs/capabilities.json').read_text(encoding='utf-8'))


def plan(task):
    catalog = capabilities()
    item = next((item for item in catalog['tasks'] if item['id'] == task), None)
    if item is None:
        raise ValueError('unknown_task')
    service = item['service']
    return {**item, 'mode': 'plan_only', 'executed': False,
            'doctor_argv': ['python3', 'wechat_ai.py', 'doctor', service],
            'help_argv': ['python3', 'wechat_ai.py', 'run', service, '--',
                          *(['batch'] if service == 'replay' else []), '--help'],
            'contract': 'skills/' + item['skill'] + '/SKILL.md'}
