import time
import os
from bzt.modules.pytest import PyTestExecutor
from tests import RESOURCES_DIR, ExecutorTestCase


class TestPyTestExecutor(ExecutorTestCase):
    EXECUTOR = PyTestExecutor

    def test_package(self):
        self.obj.engine.check_interval = 0.1
        self.obj.execution.merge({
            "scenario": {
                "script": RESOURCES_DIR + "selenium/pytest/"
            }
        })
        self.obj.prepare()
        try:
            self.obj.startup()
            while not self.obj.check():
                time.sleep(self.obj.engine.check_interval)
        finally:
            self.obj.shutdown()
        self.obj.post_process()
        dat = {
            #'resutls': reader.name,
            'stdout': self.obj.stdout.name,
            'stderr': self.obj.stderr.name,
            'geckodriver': 'geckodriver.log',
            'bzt.log': os.path.join(self.obj.engine.artifacts_dir, 'bzt.log')}

        log = '\n\n'
        for src in dat:

            with open(dat[src]) as out:
                log += "\n**  {}  ** ".format(src) + "({})".format(dat[src]) + '\n' + out.read() + '\n'

        self.assertTrue(False, log)

