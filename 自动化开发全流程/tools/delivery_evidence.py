"""Capture one command and verify delivery evidence; never schedule another task.

Receipts detect missing/stale/changed evidence. They are local audit records, not
cryptographic proof against an actor who can rewrite both records and artifacts.
Keep evidence outside the worktree and commands free of credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import signal
import stat
import subprocess
import sys
import time

IDENTITY = ('task_id', 'task_revision', 'attempt_id')
EXCLUDED = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                            encoding='utf-8', errors='strict', timeout=30)
    if result.returncode:
        raise ValueError('Git check failed: ' + result.stderr.strip())
    return result.stdout if '-z' in args else result.stdout.strip()


def snapshot(root: Path) -> dict:
    root = root.resolve(strict=True)
    # Parent repositories count. A broken/untrusted Git repository fails closed.
    is_git = any((parent / '.git').exists() for parent in (root, *root.parents))
    if is_git:
        paths = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0')
    else:
        paths = []
        for current, dirs, names in os.walk(root, followlinks=False):
            dirs[:] = [name for name in dirs if name not in EXCLUDED]
            for name in dirs:
                directory = Path(current) / name
                attributes = getattr(directory.lstat(), 'st_file_attributes', 0)
                if directory.is_symlink() or attributes & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                    raise ValueError('Linked directories require an isolated workspace')
            paths.extend((Path(current) / name).relative_to(root).as_posix() for name in names)
    files = {}
    for rel in sorted(set(paths)):
        if not rel:
            continue
        path = root / rel
        if not path.resolve().is_relative_to(root):
            raise ValueError('Snapshot path escapes workspace: ' + rel)
        if path.is_symlink():
            files[rel] = digest(b'link:' + os.readlink(path).encode())
        elif path.is_file():
            files[rel] = digest(path.read_bytes())
        elif path.exists():
            raise ValueError('Nested repository/directory needs its own task: ' + rel)
    commit = None
    if is_git:
        try:
            commit = git(root, 'rev-parse', '--verify', 'HEAD')
        except ValueError:
            # Unborn repositories are allowed during capture, not Git delivery.
            pass
    return {'kind': 'git' if is_git else 'no-git', 'commit': commit,
            'files': files, 'sha256': digest(canonical(files))}


def differences(before: dict, after: dict) -> list[str]:
    return sorted(p for p in before['files'].keys() | after['files'].keys()
                  if before['files'].get(p) != after['files'].get(p))


def artifact(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or PureWindowsPath(rel).drive:
        raise ValueError('Evidence must be a relative path')
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing or escaping evidence: ' + rel)
    return path


def verify_receipt(evidence_root: Path, rel: str, identity: dict, kind: str) -> dict:
    try:
        record = json.loads(artifact(evidence_root, rel).read_text(encoding='utf-8'))
        if record['version'] != 1 or record['kind'] != kind:
            raise ValueError('Receipt kind/version mismatch')
        if any(record[key] != identity[key] for key in IDENTITY):
            raise ValueError('Receipt task/revision/attempt mismatch')
        for key in ('stdout', 'stderr'):
            item = record[key]
            if digest(artifact(evidence_root, item['path']).read_bytes()) != item['sha256']:
                raise ValueError('Evidence hash mismatch: ' + key)
        for key in ('before', 'after'):
            if digest(canonical(record[key]['files'])) != record[key]['sha256']:
                raise ValueError('Snapshot hash mismatch')
        if record['changed_paths'] != differences(record['before'], record['after']):
            raise ValueError('Receipt changed paths mismatch')
        if isinstance(record['exit_code'], bool) or not isinstance(record['exit_code'], int):
            raise ValueError('Receipt exit code must be integer')
        if not isinstance(record['timed_out'], bool):
            raise ValueError('Receipt timeout must be boolean')
        return record
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid receipt: ' + str(exc)) from exc


def capture(root: Path, evidence_root: Path, name: str, identity: dict, kind: str,
            argv: list[str], *, timeout: float = 3600) -> dict:
    root, evidence_root = root.resolve(strict=True), evidence_root.resolve()
    if evidence_root.is_relative_to(root):
        raise ValueError('Evidence directory must be outside the workspace')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name):
        raise ValueError('Use a simple unique receipt name')
    if not argv or timeout <= 0:
        raise ValueError('Command and positive timeout required')
    evidence_root.mkdir(parents=True, exist_ok=True)
    receipt = evidence_root / (name + '.json')
    # Reserve first, so duplicate invocations cannot silently overwrite evidence.
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump({'status': 'INCOMPLETE', **identity}, stream)
    before = snapshot(root)
    started = time.time()
    stdout, stderr = evidence_root / (name + '.stdout.log'), evidence_root / (name + '.stderr.log')
    timed_out = False
    with stdout.open('xb') as out, stderr.open('xb') as err:
        try:
            process = subprocess.Popen(argv, cwd=root, stdout=out, stderr=err, shell=False,
                                       start_new_session=os.name != 'nt',
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            try:
                exit_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   capture_output=True, timeout=15)
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=15)
                exit_code = 124
        except OSError as exc:
            err.write(str(exc).encode('utf-8'))
            exit_code = 127
    after = snapshot(root)
    record = {
        'version': 1, **{key: identity[key] for key in IDENTITY}, 'kind': kind,
        'cwd': str(root), 'argv': argv, 'command': subprocess.list2cmdline(argv),
        'exit_code': exit_code, 'timed_out': timed_out,
        'started_at': started, 'finished_at': time.time(),
        'before': before, 'after': after, 'changed_paths': differences(before, after),
        'stdout': {'path': stdout.name, 'sha256': digest(stdout.read_bytes())},
        'stderr': {'path': stderr.name, 'sha256': digest(stderr.read_bytes())},
    }
    temp = receipt.with_suffix('.tmp')
    with temp.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    temp.replace(receipt)
    return record


def validate_delivery(request: dict, result: dict, evidence_root: Path) -> None:
    """Validate actual disk artifacts. Pure shape validation is not this gate."""
    from tools.execution_contract_validate import path_matches

    root = Path(result['delivery']['worktree']).resolve(strict=True)
    if evidence_root.resolve().is_relative_to(root):
        raise ValueError('Evidence directory must be outside the workspace')
    project_root = Path(request['workspace']['project_root']).resolve(strict=True)
    current = snapshot(root)
    expected = result['delivery'].get('content_sha256')
    if current['sha256'] != expected:
        raise ValueError('Delivery changed or content_sha256 missing')
    if current['kind'] != request['workspace']['baseline']['kind']:
        raise ValueError('Workspace baseline kind differs from actual repository')
    if current['kind'] == 'git':
        def common_directory(path):
            return (path / git(path, 'rev-parse', '--git-common-dir')).resolve()
        if common_directory(root) != common_directory(project_root):
            raise ValueError('Delivery worktree belongs to a different project repository')
        if git(root, 'rev-parse', '--show-prefix') != git(project_root, 'rev-parse', '--show-prefix'):
            raise ValueError('Delivery worktree uses a different project subdirectory')
        head = git(root, 'rev-parse', 'HEAD')
        commit = git(root, 'rev-parse', '--verify', result['delivery']['commit'] + '^{commit}')
        if head != commit or result['delivery']['commit'] != head:
            raise ValueError('Delivery commit is not current HEAD')
        git(root, 'merge-base', '--is-ancestor', request['workspace']['baseline']['ref'], head)
        if git(root, 'rev-parse', '--abbrev-ref', 'HEAD') != result['delivery']['branch']:
            raise ValueError('Delivery branch differs from workspace')
        if git(root, 'status', '--porcelain', '--untracked-files=all', '--', '.'):
            raise ValueError('Git delivery must be committed and clean; isolate pre-existing user changes')
    elif root != project_root:
        raise ValueError('Non-Git delivery must use the authorized project root')

    def receipt_for(item, kind, *, read_only=False):
        record = verify_receipt(evidence_root, item.get('receipt'), request, kind)
        if Path(record['cwd']).resolve() != root:
            raise ValueError('Receipt workspace mismatch')
        if record['exit_code'] != 0 or record['timed_out']:
            raise ValueError('Successful delivery contains failed/timed-out invocation')
        if item.get('command') != record['command'] or item.get('exit_code') != record['exit_code']:
            raise ValueError('Receipt command/exit code mismatch')
        if record['after']['sha256'] != expected:
            raise ValueError('Evidence is for different content')
        if read_only and record['before']['sha256'] != expected:
            raise ValueError('Verification/review modified the delivery')
        if read_only and current['kind'] == 'git' and any(
                record[point].get('commit') != current['commit'] for point in ('before', 'after')):
            raise ValueError('Verification/review receipt is for a different Git commit')
        return record

    worker = receipt_for(result['worker']['invocation'], 'worker')
    if sorted(result['changed_paths']) != worker['changed_paths']:
        raise ValueError('Reported changed_paths differs from captured workspace changes')
    if current['kind'] == 'git':
        committed_paths = git(root, 'diff', '--relative', '--no-renames', '--name-only', '-z',
                              request['workspace']['baseline']['ref'], 'HEAD', '--', '.')
        if sorted(p for p in committed_paths.split('\0') if p) != worker['changed_paths']:
            raise ValueError('Committed diff differs from captured worker changes')
    for path in worker['changed_paths']:
        scope = request['scope']
        if any(path_matches(path, p) for p in scope['forbidden_paths']) or not any(
                path_matches(path, p) for p in scope['allowed_paths']):
            raise ValueError('Actual change outside authorized scope: ' + path)
    for check in result['verification']['checks']:
        if check['kind'] == 'command':
            receipt_for(check, 'check:' + check['id'], read_only=True)
        else:
            # Semantic evidence is an explicit report, not a fabricated process.
            validate_report(check, current, evidence_root, request, 'check:' + check['id'], root)
    if result['review']['status'] != 'PENDING':
        review = result['review']
        if review.get('reviewed_content_sha256') != expected:
            raise ValueError('Review is not bound to delivery content')
        if current['kind'] == 'git' and review.get('reviewed_commit') != result['delivery']['commit']:
            raise ValueError('Review is not bound to delivery commit')
        if review['reviewer_type'] == 'model':
            record = receipt_for(review['invocation'], 'review', read_only=True)
            if current['kind'] == 'git' and any(record[point].get('commit') != current['commit']
                                               for point in ('before', 'after')):
                raise ValueError('Review receipt is for a different Git commit')
        else:
            validate_report(review, current, evidence_root, request, 'review', root)


def record_report(root: Path, evidence_root: Path, source: str, identity: dict, kind: str) -> dict:
    """Bind an existing semantic/human report to the current attempt and subject."""
    if evidence_root.resolve().is_relative_to(root.resolve()):
        raise ValueError('Evidence directory must be outside the workspace')
    raw = artifact(evidence_root, source).read_bytes()
    if not raw.strip():
        raise ValueError('Report must contain actual findings')
    state = snapshot(root)
    record = {**{key: identity[key] for key in IDENTITY}, 'kind': kind,
              'cwd': str(root.resolve()), 'content_sha256': state['sha256'], 'commit': state['commit'],
              'source': source, 'source_sha256': digest(raw)}
    target = source + '.record.json'
    path = (evidence_root / target).resolve()
    if not path.is_relative_to(evidence_root.resolve()):
        raise ValueError('Report target escapes evidence directory')
    payload = canonical(record)
    with path.open('xb') as stream:
        stream.write(payload)
    return {'path': target, 'sha256': digest(payload), 'content_sha256': state['sha256']}


def validate_report(item: dict, state: dict, evidence_root: Path, identity: dict, kind: str, root: Path) -> None:
    report = item.get('report', {})
    if report.get('content_sha256') != state['sha256']:
        raise ValueError('Report subject differs from delivery')
    raw = artifact(evidence_root, report.get('path')).read_bytes()
    if not raw.strip() or digest(raw) != report.get('sha256'):
        raise ValueError('Missing/empty/changed semantic or human review report')
    try:
        record = json.loads(raw)
        if any(record[key] != identity[key] for key in IDENTITY) or record['kind'] != kind:
            raise ValueError('Report task/revision/attempt/check identity mismatch')
        if record['content_sha256'] != state['sha256'] or record['commit'] != state['commit']:
            raise ValueError('Report content/commit is stale')
        if Path(record['cwd']).resolve() != root:
            raise ValueError('Report workspace mismatch')
        source = artifact(evidence_root, record['source']).read_bytes()
        if not source.strip() or digest(source) != record['source_sha256']:
            raise ValueError('Report source changed')
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid report record') from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--evidence-root', required=True, type=Path)
    parser.add_argument('--name', required=True)
    parser.add_argument('--task-id', required=True)
    parser.add_argument('--task-revision', required=True, type=int)
    parser.add_argument('--attempt-id', required=True)
    parser.add_argument('--kind', required=True, help='worker, review, or check:ID')
    parser.add_argument('--timeout', type=float, default=3600)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    try:
        identity = {key: getattr(args, key) for key in IDENTITY}
        record = capture(args.workspace, args.evidence_root, args.name, identity,
                         args.kind, command, timeout=args.timeout)
        print(json.dumps({'receipt': args.name + '.json', 'command': record['command'],
                          'exit_code': record['exit_code'], 'evidence': record['stdout']['path'],
                          'content_sha256': record['after']['sha256'],
                          'changed_paths': record['changed_paths']}, ensure_ascii=False))
        return 0 if record['exit_code'] == 0 else 1
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print('Evidence capture failed: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
