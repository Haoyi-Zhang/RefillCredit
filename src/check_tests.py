"""Run and retain counts for the owned certificate-mutation regression suite."""
import json,sys,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
suite=unittest.defaultTestLoader.discover(str(root/'tests'))
result=unittest.TextTestRunner(verbosity=1).run(suite)
record={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'skipped':len(result.skipped),'successful':result.wasSuccessful(),
        'scope':'owned finite-model input, certificate, witness and boundary tests'}
(root/'results/unit-tests.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
sys.exit(0 if result.wasSuccessful() else 1)
