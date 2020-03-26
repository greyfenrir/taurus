import time

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

