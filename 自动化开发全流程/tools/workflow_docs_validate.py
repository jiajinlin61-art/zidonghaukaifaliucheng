"""Validate local Markdown references and lean entrypoint constraints."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def validate(root=ROOT):
    issues=[]
    entrypoints=['AGENTS.md','ai-development-workflow-v1/PROJECT_EXECUTION_RULES.md',
                 'ai-development-workflow-v1/CODEX_MASTER_PROMPT.md',
                 'ai-development-workflow-v1/starter-project/AGENTS.md']
    for rel in entrypoints:
        path=root/rel
        if not path.is_file():
            issues.append('Missing entry: '+rel)
        elif len(path.read_text(encoding='utf-8').splitlines())>45:
            issues.append('Entrypoint exceeds 45 lines: '+rel)
    files=[root/'README.md',root/'AGENTS.md',*(root/'ai-development-workflow-v1').rglob('*.md')]
    for path in files:
        text=path.read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if '://' in target or target.startswith('#') or '<' in target:
                continue
            target=target.split('#')[0]
            if target and not (path.parent/target).exists():
                issues.append(f'{path.relative_to(root)}: missing link {target}')
        if 'FAST 只在未命中上述 Gate 条件时允许直接' in text:
            issues.append(f'{path.relative_to(root)}: obsolete approval exception')
    return issues


if __name__=='__main__':
    issues=validate()
    for issue in issues:
        print(issue)
    print(f'Workflow docs: {len(issues)} issues')
    raise SystemExit(bool(issues))
