import copy
from pathlib import Path
import sys
import tempfile
import unittest

from tools.delivery_evidence import capture
from tools.project_acceptance_validate import validate_coverage, validate_integration


class ProjectAcceptanceTest(unittest.TestCase):
    def plan(self):
        return {'approval_ref':'user-approved-plan',
                'requirements':[{'id':'R1','criterion':'A user can save and reopen a record'},
                                {'id':'R2','criterion':'Invalid input is rejected'}],
                'tasks':[{'id':'T1','requirement_ids':['R1','R2']}],
                'checks':[{'id':'I1','requirement_ids':['R1','R2'],'command':'integration'}]}

    def test_detect_missing_unknown_duplicate_requirement_mappings(self):
        validate_coverage(self.plan())
        for change in [lambda p:p['tasks'][0].update(requirement_ids=['R1']),
                       lambda p:p['checks'][0].update(requirement_ids=['R1']),
                       lambda p:p['checks'][0].update(requirement_ids=['R1','unknown']),
                       lambda p:p['requirements'].append(p['requirements'][0])]:
            plan=self.plan()
            change(plan)
            with self.assertRaises(ValueError):
                validate_coverage(plan)

    def test_actual_integration_and_stale_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            root=base/'project'
            root.mkdir()
            (root/'data.txt').write_text('saved')
            identity={'task_id':'project-acceptance','task_revision':1,'attempt_id':'integration-1'}
            record=capture(root,base/'evidence','integration',identity,'check:I1',
                           [sys.executable,'-c',"from pathlib import Path; assert Path('data.txt').read_text() == 'saved'"])
            plan=self.plan()
            plan.update(workspace=str(root),integration_identity=identity)
            plan['checks'][0].update(command=record['command'],receipt='integration.json')
            validate_integration(plan,base/'evidence')
            (root/'data.txt').write_text('broken')
            with self.assertRaises(ValueError):
                validate_integration(plan,base/'evidence')
