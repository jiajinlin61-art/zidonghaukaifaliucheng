"""Populate evidence fields of an existing result; never invent success/review conclusions."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yaml
from tools.delivery_evidence import record_report, verify_receipt
from tools.execution_contract_validate import load_yaml


def populate(request, result, evidence_root, worker=None, checks=(), review=None):
    if any(request.get(k) != result.get(k) for k in ('task_id','task_revision','attempt_id')):
        raise ValueError('Request/result identity mismatch')
    def fields(rel, kind):
        record=verify_receipt(evidence_root, rel, request, kind)
        return record, dict(command=record['command'], exit_code=record['exit_code'],
                            evidence=record['stdout']['path'], receipt=rel)
    if worker:
        record, invocation=fields(worker,'worker')
        result['worker']['invocation']=invocation
        result['delivery']['content_sha256']=record['after']['sha256']
        result['changed_paths']=record['changed_paths']
    indexed={item['id']:item for item in result['verification']['checks']}
    required={item['id']:item for item in request['validation']['required_checks']}
    for assignment in checks:
        check_id,rel=assignment.split('=',1)
        if check_id not in required or required[check_id]['kind']!='command':
            raise ValueError('Unknown/non-command check: '+check_id)
        record,invocation=fields(rel,'check:'+check_id)
        if record['command']!=required[check_id]['command']:
            raise ValueError('Captured command differs from required check '+check_id)
        indexed[check_id]=dict(id=check_id,kind='command',**invocation)
    result['verification']['checks']=list(indexed.values())
    if review:
        record,invocation=fields(review,'review')
        if record['before']['sha256']!=record['after']['sha256']:
            raise ValueError('Review changed delivery files')
        result['review']['invocation']=invocation
        result['review']['reviewed_content_sha256']=record['after']['sha256']
        result['review']['reviewed_commit']=record['after'].get('commit')
    return result


def atomic_write(path: Path, text: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--result',type=Path,required=True)
    parser.add_argument('--evidence-root',type=Path,required=True)
    parser.add_argument('--worker',help='Worker receipt relative path')
    parser.add_argument('--check',action='append',default=[],help='ID=receipt.json; repeatable')
    parser.add_argument('--review',help='Reviewer receipt relative path')
    parser.add_argument('--semantic',action='append',default=[],help='ID=existing-report.txt; bind real findings')
    parser.add_argument('--human-review',help='Existing human review report relative to evidence root')
    args=parser.parse_args()
    try:
        request=load_yaml(args.request)
        result=populate(request,load_yaml(args.result),args.evidence_root,
                        args.worker,args.check,args.review)
        root=Path(result['delivery']['worktree']).resolve(strict=True)
        required={item['id']:item for item in request['validation']['required_checks']}
        for assignment in args.semantic:
            check_id,source=assignment.split('=',1)
            if check_id not in required or required[check_id]['kind']!='semantic':
                raise ValueError('Unknown/non-semantic check: '+check_id)
            item=next(check for check in result['verification']['checks'] if check['id']==check_id)
            item['report']=record_report(root,args.evidence_root,source,request,'check:'+check_id)
        if args.human_review:
            if result['review']['reviewer_type']!='human':
                raise ValueError('--human-review requires an actual human reviewer')
            report=record_report(root,args.evidence_root,args.human_review,request,'review')
            result['review']['report']=report
            result['review']['reviewed_content_sha256']=report['content_sha256']
            result['review']['reviewed_commit']=result['delivery'].get('commit')
        text=yaml.safe_dump(result,allow_unicode=True,sort_keys=False)
        # This is explicitly an update command. Preserve existing unrelated fields.
        atomic_write(args.result,text)
    except (OSError,ValueError,KeyError,TypeError,StopIteration,yaml.YAMLError) as exc:
        print('Result update failed: '+str(exc),file=sys.stderr)
        return 1
    print('Evidence fields updated; status, route, sessions and review conclusion still require actual evidence')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
