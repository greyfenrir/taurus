import time
import os
from bzt.modules.selenium import GeckoDriver
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
        driver = self.obj._get_tool(GeckoDriver, config=self.obj.settings.get('geckodriver'))
        if not driver.check_if_installed():
            driver.install()
        self.obj.env.add_path({"PATH": driver.get_driver_dir()})
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
            'PyTestExecutor.ldjson': os.path.join(self.obj.engine.artifacts_dir, 'PyTestExecutor.ldjson')}

        log = '\n\n'
        for src in dat:

            with open(dat[src]) as out:
                log += "\n**  {}  ** ".format(src) + "({})".format(dat[src]) + '\n' + out.read() + '\n'

        self.assertTrue(False, log)

