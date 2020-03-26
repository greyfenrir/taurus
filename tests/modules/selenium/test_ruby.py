import bzt
import os
from bzt.utils import EXE_SUFFIX
from tests import RESOURCES_DIR
from tests.modules.selenium import SeleniumTestCase


class TestSeleniumRSpecRunner(SeleniumTestCase):
    CMD_LINE = None

    def start_subprocess(self, args, **kwargs):
        self.CMD_LINE = ' '.join(args)

    def exec_and_communicate(self, *args, **kwargs):
        return "", ""

    def test_rspec_full(self):
        if os.path.exists("geckodriver.log"):
            self.fail('geckodriver found (suddenly)')

        config = {
            'execution': {
                'hold-for': '10s',
                'iterations': 3,
                'scenario': {'script': RESOURCES_DIR + 'selenium/ruby/example_spec.rb'},
            },
        }
        self.configure(config)
        dummy = RESOURCES_DIR + 'selenium/ruby/ruby' + EXE_SUFFIX

        tmp_aec = bzt.utils.exec_and_communicate
        try:
            bzt.utils.exec_and_communicate = self.exec_and_communicate
            self.obj.prepare()
        finally:
            bzt.utils.exec_and_communicate = tmp_aec

        self.obj.runner.settings.merge({"interpreter": dummy})
        self.obj.engine.start_subprocess = self.start_subprocess
        self.obj.startup()
        self.obj.shutdown()
        self.obj.post_process()
