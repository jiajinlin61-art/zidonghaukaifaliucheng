import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.execution_contract_validate import validate_result
from test_execution_contract_validate import valid_result, complete_model_review


class SuccessSemanticsTest(unittest.TestCase):
    def test_failed_worker_process_cannot_be_completed(self):
        result = valid_result()
        result['worker']['invocation']['exit_code'] = 1
        with self.assertRaises(ValueError):
            validate_result(result)

    def test_failed_reviewer_process_cannot_pass(self):
        result = valid_result()
        complete_model_review(result)
        result['review']['invocation']['exit_code'] = 1
        with self.assertRaises(ValueError):
            validate_result(result)


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        from tools.delivery_evidence import capture, snapshot, verify_receipt
        self.capture, self.snapshot, self.verify = capture, snapshot, verify_receipt
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'project'
        self.root.mkdir()
        self.evidence = self.base / 'evidence'
        self.identity = dict(task_id='T1', task_revision=1, attempt_id='T1-r1-a1')

    def run_capture(self, code, name='worker', kind='worker'):
        return self.capture(self.root, self.evidence, name, self.identity, kind,
                            [sys.executable, '-c', code], timeout=10)

    def test_capture_cli_keeps_two_projects_and_exit_codes_separate(self):
        tool = Path(__file__).resolve().parents[1] / 'tools' / 'delivery_evidence.py'
        receipts = []
        for name, exit_code in [('project-a', 0), ('project-b', 7)]:
            with self.subTest(project=name):
                workspace = self.base / name
                workspace.mkdir()
                evidence = self.base / (name + '-evidence')
                code = ("from pathlib import Path; Path('owned.txt').write_text("
                        + repr(name) + "); print(" + repr(name)
                        + "); raise SystemExit(" + str(exit_code) + ")")
                process = subprocess.run(
                    [sys.executable, '-B', str(tool), '--workspace', str(workspace),
                     '--evidence-root', str(evidence), '--name', 'worker',
                     '--task-id', 'T1', '--task-revision', '1',
                     '--attempt-id', 'T1-r1-a1', '--kind', 'worker', '--',
                     sys.executable, '-B', '-c', code], cwd=workspace,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(process.returncode, 0 if exit_code == 0 else 1,
                                 process.stderr)
                self.assertEqual(json.loads(process.stdout)['exit_code'], exit_code)
                record = self.verify(evidence, 'worker.json', self.identity, 'worker')
                self.assertEqual(Path(record['cwd']), workspace)
                self.assertEqual(record['exit_code'], exit_code)
                self.assertEqual(record['changed_paths'], ['owned.txt'])
                self.assertEqual((workspace / 'owned.txt').read_text(), name)
                self.assertEqual((evidence / record['stdout']['path']).read_text().strip(), name)
                receipts.append(evidence / 'worker.json')
        self.assertNotEqual(receipts[0].read_bytes(), receipts[1].read_bytes())

    def test_capture_real_process_and_detect_tampered_log(self):
        record = self.run_capture("from pathlib import Path; Path('file.txt').write_text('ok'); print('ran')")
        loaded = self.verify(self.evidence, 'worker.json', self.identity, 'worker')
        self.assertEqual(loaded['exit_code'], 0)
        self.assertEqual(loaded['changed_paths'], ['file.txt'])
        (self.evidence / record['stdout']['path']).write_text('tampered')
        with self.assertRaises(ValueError):
            self.verify(self.evidence, 'worker.json', self.identity, 'worker')

    def test_failure_and_timeout_are_recorded(self):
        record = self.run_capture('raise SystemExit(7)')
        self.assertEqual(record['exit_code'], 7)
        record = self.capture(self.root, self.evidence, 'slow', self.identity, 'worker',
                              [sys.executable, '-c', 'import time; time.sleep(5)'], timeout=0.1)
        self.assertTrue(record['timed_out'])
        self.assertNotEqual(record['exit_code'], 0)

    def test_preexisting_dirty_file_is_not_claimed_as_task_change(self):
        (self.root / 'user.txt').write_text('user work')
        record = self.run_capture("from pathlib import Path; Path('task.txt').write_text('new')")
        self.assertEqual(record['changed_paths'], ['task.txt'])
        self.assertIn('user.txt', record['before']['files'])

    def test_wrong_attempt_and_path_escape_rejected(self):
        self.run_capture("print('ok')")
        wrong = dict(self.identity, attempt_id='other')
        for path, identity in [('worker.json', wrong), ('../worker.json', self.identity), ('missing.json', self.identity)]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.verify(self.evidence, path, identity, 'worker')

    def test_receipt_cannot_be_overwritten(self):
        self.run_capture("print('ok')")
        with self.assertRaises((ValueError, FileExistsError)):
            self.run_capture("raise SystemExit(0)")

    def test_git_tracks_ignored_but_tracked_files_and_deletions(self):
        def git(*args):
            return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        git('init')
        (self.root / 'tracked.txt').write_text('old')
        git('add', 'tracked.txt')
        (self.root / '.gitignore').write_text('tracked.txt\ncache/\n')
        (self.root / 'cache').mkdir()
        (self.root / 'cache' / 'ignored').write_text('irrelevant')
        state = self.snapshot(self.root)
        self.assertIn('tracked.txt', state['files'])
        self.assertNotIn('cache/ignored', state['files'])
        record = self.run_capture("from pathlib import Path; Path('tracked.txt').unlink()")
        self.assertEqual(record['changed_paths'], ['tracked.txt'])

    def delivery_fixture(self, use_git=False):
        from tools.delivery_evidence import git
        if use_git:
            git(self.root, 'init')
            git(self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                'commit', '--allow-empty', '-m', 'baseline')
        baseline = git(self.root, 'rev-parse', 'HEAD') if use_git else 'initial-files'
        worker = self.run_capture("from pathlib import Path; Path('file.txt').write_text('ok')")
        if use_git:
            git(self.root, 'add', 'file.txt')
            git(self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'task')
        check = self.run_capture("from pathlib import Path; assert Path('file.txt').read_text() == 'ok'", 'check', 'check:V1')
        review = self.run_capture("print('independent process review fixture')", 'review', 'review')
        def invocation(record, name):
            return dict(command=record['command'], exit_code=record['exit_code'], receipt=name+'.json')
        request = dict(self.identity, workspace={'project_root': str(self.root), 'baseline': {'kind': 'git' if use_git else 'no-git', 'ref': baseline}},
                       scope={'allowed_paths': ['file.txt'], 'forbidden_paths': []})
        commit = git(self.root, 'rev-parse', 'HEAD') if use_git else None
        result = dict(changed_paths=['file.txt'],
                      delivery={'worktree': str(self.root), 'content_sha256': worker['after']['sha256'],
                                'commit': commit, 'branch': git(self.root, 'rev-parse', '--abbrev-ref', 'HEAD') if use_git else None},
                      worker={'invocation': invocation(worker, 'worker')},
                      verification={'checks': [dict(id='V1', kind='command', **invocation(check, 'check'))]},
                      review={'status':'PASS', 'reviewer_type':'model', 'invocation':invocation(review, 'review'),
                              'reviewed_content_sha256':worker['after']['sha256'], 'reviewed_commit':commit})
        return request, result

    def test_real_delivery_and_adversarial_mutations(self):
        from tools.delivery_evidence import validate_delivery
        request, result = self.delivery_fixture()
        validate_delivery(request, result, self.evidence)
        mutations = [
            lambda r: r.update(changed_paths=[]),
            lambda r: r['worker']['invocation'].update(receipt='missing.json'),
            lambda r: r['review'].update(reviewed_content_sha256='stale'),
            lambda r: r['verification']['checks'][0].update(command='different command'),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(result)
            mutate(changed)
            with self.assertRaises(ValueError):
                validate_delivery(request, changed, self.evidence)
        request['scope']['allowed_paths'] = ['elsewhere/**']
        with self.assertRaises(ValueError):
            validate_delivery(request, result, self.evidence)
        request['scope']['allowed_paths'] = ['file.txt']
        (self.root / 'file.txt').write_text('changed after review')
        with self.assertRaises(ValueError):
            validate_delivery(request, result, self.evidence)

    def test_real_git_review_is_bound_to_commit(self):
        from tools.delivery_evidence import validate_delivery, git
        request, result = self.delivery_fixture(use_git=True)
        validate_delivery(request, result, self.evidence)
        git(self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '--allow-empty', '-m', 'after review')
        result['delivery']['commit'] = git(self.root, 'rev-parse', 'HEAD')
        result['review']['reviewed_commit'] = result['delivery']['commit']
        with self.assertRaisesRegex(ValueError, 'different Git commit'):
            validate_delivery(request, result, self.evidence)

    def test_git_uncommitted_delivery_cannot_use_old_head(self):
        from tools.delivery_evidence import validate_delivery, git
        request, result = self.delivery_fixture(use_git=True)
        git(self.root, 'reset', '--soft', request['workspace']['baseline']['ref'])
        result['delivery']['commit'] = request['workspace']['baseline']['ref']
        result['review']['reviewed_commit'] = result['delivery']['commit']
        with self.assertRaisesRegex(ValueError, 'committed and clean'):
            validate_delivery(request, result, self.evidence)

    def test_git_baseline_cannot_hide_committed_changes(self):
        from tools.delivery_evidence import validate_delivery
        request, result = self.delivery_fixture(use_git=True)
        request['workspace']['baseline']['ref'] = result['delivery']['commit']
        with self.assertRaisesRegex(ValueError, 'Committed diff'):
            validate_delivery(request, result, self.evidence)

    def test_old_check_receipt_cannot_pass_after_new_commit(self):
        from tools.delivery_evidence import validate_delivery, git
        request, result = self.delivery_fixture(use_git=True)
        result['review']['status'] = 'PENDING'
        git(self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '--allow-empty', '-m', 'new commit after tests')
        result['delivery']['commit'] = git(self.root, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'different Git commit'):
            validate_delivery(request, result, self.evidence)

    def test_report_binds_attempt_and_source(self):
        from tools.delivery_evidence import record_report, validate_report
        self.evidence.mkdir()
        (self.evidence/'findings.txt').write_text('Human checked acceptance and actual diff')
        report = record_report(self.root,self.evidence,'findings.txt',self.identity,'review')
        state=self.snapshot(self.root)
        validate_report({'report':report},state,self.evidence,self.identity,'review',self.root)
        with self.assertRaisesRegex(ValueError,'identity mismatch'):
            validate_report({'report':report},state,self.evidence,dict(self.identity,attempt_id='other'),'review',self.root)
        (self.evidence/'findings.txt').write_text('replaced')
        with self.assertRaisesRegex(ValueError,'source changed'):
            validate_report({'report':report},state,self.evidence,self.identity,'review',self.root)

    def test_result_update_failure_preserves_original(self):
        from unittest.mock import patch
        from tools.evidence_result_update import atomic_write
        target=self.base/'result.yaml'
        target.write_text('original',encoding='utf-8')
        with patch('tools.evidence_result_update.os.replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                atomic_write(target,'replacement')
        self.assertEqual(target.read_text(encoding='utf-8'),'original')
        self.assertEqual(list(self.base.glob('result.yaml.*.tmp')),[])
        atomic_write(target,'replacement')
        self.assertEqual(target.read_text(encoding='utf-8'),'replacement')

    def test_full_actual_cli_and_automatic_fields(self):
        import yaml
        from tools.evidence_result_update import populate
        from test_execution_contract_validate import valid_request
        captured_request, captured_result = self.delivery_fixture()
        request, result = valid_request(), valid_result()
        request.update(self.identity)
        result.update(self.identity)
        request['workspace'] = captured_request['workspace']
        result['workspace'] = copy.deepcopy(request['workspace'])
        request['scope'] = captured_request['scope']
        request['validation'] = {'mode':'commands','required_checks':[
            {'id':'V1','kind':'command','acceptance_ids':['A1','A2'],
             'command':captured_result['verification']['checks'][0]['command']}]}
        result['delivery'] = captured_result['delivery']
        result['verification'] = {'mode':'commands','result':'PASS','checks':[]}
        complete_model_review(result)
        populate(request,result,self.evidence,'worker.json',['V1=check.json'],'review.json')
        before_status=result['status']
        self.assertEqual(before_status,'REVIEW_PASSED')
        req,res=self.base/'request.yaml',self.base/'result.yaml'
        req.write_text(yaml.safe_dump(request),encoding='utf-8')
        res.write_text(yaml.safe_dump(result),encoding='utf-8')
        cli=Path(__file__).resolve().parents[1]/'tools'/'execution_contract_validate.py'
        command=[sys.executable,'-B',str(cli),'--request',str(req),'--result',str(res)]
        missing=subprocess.run(command,capture_output=True,text=True)
        self.assertNotEqual(missing.returncode,0)
        self.assertIn('--evidence-root',missing.stderr)
        passed=subprocess.run(command+['--evidence-root',str(self.evidence)],capture_output=True,text=True)
        self.assertEqual(passed.returncode,0,passed.stderr)
        (self.root/'file.txt').write_text('changed')
        stale=subprocess.run(command+['--evidence-root',str(self.evidence)],capture_output=True,text=True)
        self.assertNotEqual(stale.returncode,0)


if __name__ == '__main__':
    unittest.main()
