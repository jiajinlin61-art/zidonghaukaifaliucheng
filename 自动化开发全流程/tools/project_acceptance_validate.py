"""Check project requirement coverage and fresh integration evidence (not DONE)."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yaml
from tools.delivery_evidence import snapshot, verify_receipt
from tools.execution_contract_validate import load_yaml, nonempty_string, string_list


def validate_coverage(plan: dict) -> None:
    nonempty_string(plan.get('approval_ref'), 'approval_ref')
    requirements = plan.get('requirements')
    tasks = plan.get('tasks')
    checks = plan.get('checks')
    if not all(isinstance(items, list) and items for items in (requirements, tasks, checks)):
        raise ValueError('requirements, tasks and checks must be nonempty lists')
    def index(items, label):
        mapped = {}
        for item in items:
            key = nonempty_string(item.get('id'), label + '.id')
            if key in mapped:
                raise ValueError('Duplicate ' + label + ' id: ' + key)
            mapped[key] = item
        return mapped
    reqs, work, verification = index(requirements, 'requirement'), index(tasks, 'task'), index(checks, 'check')
    for item in reqs.values():
        nonempty_string(item.get('criterion'), 'requirement.criterion')
    for item in verification.values():
        nonempty_string(item.get('command'), 'check.command')
    for items, label in ((work, 'task'), (verification, 'check')):
        covered = set()
        for item in items.values():
            linked = set(string_list(item.get('requirement_ids'), label+'.requirement_ids', allow_empty=False))
            if linked - reqs.keys():
                raise ValueError('Unknown requirement referenced by ' + label)
            covered.update(linked)
        missing = reqs.keys() - covered
        if missing:
            raise ValueError('Requirements without ' + label + ': ' + ', '.join(sorted(missing)))


def validate_integration(plan: dict, evidence_root: Path) -> None:
    validate_coverage(plan)
    root = Path(plan['workspace']).resolve(strict=True)
    content = snapshot(root)
    for check in plan['checks']:
        record = verify_receipt(evidence_root, check['receipt'], plan['integration_identity'], 'check:'+check['id'])
        if Path(record['cwd']).resolve() != root:
            raise ValueError('Integration receipt belongs to another workspace')
        if record['command'] != check['command'] or record['exit_code'] != 0 or record['timed_out']:
            raise ValueError('Integration command failed or differs from approved check')
        for point in ('before', 'after'):
            if record[point]['sha256'] != content['sha256'] or record[point].get('commit') != content.get('commit'):
                raise ValueError('Integration evidence is stale or changed the project')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--evidence-root', type=Path)
    parser.add_argument('--coverage-only', action='store_true', help='Planning check only, never delivery acceptance')
    args = parser.parse_args()
    try:
        plan = load_yaml(args.plan)
        validate_coverage(plan)
        if not args.coverage_only:
            if args.evidence_root is None:
                raise ValueError('Integration requires --evidence-root')
            validate_integration(plan, args.evidence_root)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print('Project acceptance failed: '+str(exc), file=sys.stderr)
        return 1
    print('Coverage mapping passed (not acceptance)' if args.coverage_only else
          'Requirement coverage and integration evidence passed (Controller still owns DONE)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
