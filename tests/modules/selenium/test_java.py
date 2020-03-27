import os
import shutil
import time
from os.path import exists, join, dirname

from bzt.modules.aggregator import ConsolidatingAggregator, KPISet
from bzt.modules.functional import FunctionalAggregator, FuncSamplesReader
from bzt.modules.java import JUnitTester, TestNGTester
from bzt.modules.java.tools import JarTool, Hamcrest
from bzt.modules.jmeter import JTLReader
from bzt.modules.selenium import SeleniumExecutor
from tests import BZTestCase, local_paths_config, RESOURCES_DIR, BUILD_DIR, ExecutorTestCase
from tests.mocks import EngineEmul


class TestTestNGTester(ExecutorTestCase):
    EXECUTOR = TestNGTester

    def setUp(self):
        super(TestTestNGTester, self).setUp()
        pass
        #self.obj.engine.configure([local_paths_config()])
        #self.obj.settings = self.obj.engine.config.get("modules").get("testng")
        #raise BaseException('in testtestngtester!')


class TestJUnitTester(BZTestCase):
    def setUp(self):
        super(TestJUnitTester, self).setUp()
        engine_obj = EngineEmul()
        paths = [local_paths_config()]
        engine_obj.configure(paths)

        # just download geckodriver & chromedriver with selenium
        selenium = SeleniumExecutor()
        selenium.engine = engine_obj
        selenium.install_required_tools()
        for driver in selenium.webdrivers:
            selenium.env.add_path({"PATH": driver.get_driver_dir()})

        self.obj = JUnitTester()
        self.obj.env = selenium.env
        self.obj.settings = engine_obj.config.get("modules").get("junit")
        self.obj.engine = engine_obj

    def tearDown(self):
        if self.obj.stdout:
            self.obj.stdout.close()
        if self.obj.stderr:
            self.obj.stderr.close()
        super(TestJUnitTester, self).tearDown()

    def test_install_tools(self):
        """
        check installation of selenium-server, junit
        :return:
        """
        installation_path = BUILD_DIR + "selenium-taurus"
        source_url = "file:///" + RESOURCES_DIR + "selenium/selenium-server.jar"

        shutil.rmtree(dirname(installation_path), ignore_errors=True)
        self.assertFalse(exists(installation_path))

        saved_url = JarTool.URL
        saved_local_path = JarTool.LOCAL_PATH

        JarTool.URL = source_url
        JarTool.LOCAL_PATH = join(installation_path, "{tool_file}")

        try:
            self.obj.settings.merge({
                "selenium-server": join(installation_path, "selenium-server.jar"),
                "hamcrest-core": {
                    "path": join(installation_path, "tools", "junit", "hamcrest-core.jar"),
                    "version": "0.1",
                },
                "path": installation_path
            })

            self.obj.execution.merge({
                "scenario": {
                    "script": RESOURCES_DIR + "selenium/junit/jar/"},
                "runner": "junit"})
            self.obj.prepare()
        finally:
            JarTool.URL = saved_url
            JarTool.LOCAL_PATH = saved_local_path

        self.assertTrue(isinstance(self.obj, JUnitTester))

        jar_tools = [tool for tool in self.obj._tools if isinstance(tool, JarTool)]
        self.assertTrue(15, len(jar_tools))

        for tool in jar_tools:
            msg = "Wrong path to {tool}: {path}".format(tool=str(tool), path=str(tool.tool_path))
            if isinstance(tool, Hamcrest):
                self.assertEqual(tool.version, "0.1")
            self.assertTrue(os.path.isfile(tool.tool_path), msg)

    def test_simple(self):
        self.obj.engine.aggregator = ConsolidatingAggregator()
        self.obj.execution.merge({
            "scenario": {"script": RESOURCES_DIR + "BlazeDemo.java", "properties": {"scenprop": 3}},
            "properties": {"execprop": 2}
        })
        self.obj.settings.merge({"properties": {"settprop": 1}, "junit-version": 5})
        self.obj.prepare()
        self.obj.engine.aggregator.prepare()
        self.obj.startup()
        while not self.obj.check():
            time.sleep(self.obj.engine.check_interval)
        self.obj.shutdown()
        self.obj.post_process()
        self.obj.engine.aggregator.post_process()

        orig_prop_file = RESOURCES_DIR + "selenium/junit/runner.properties"
        start1 = (self.obj.engine.artifacts_dir + os.path.sep).replace('\\', '/')
        start2 = "ARTIFACTS+"
        self.assertFilesEqual(orig_prop_file, self.obj.props_file, replace_str=start1, replace_with=start2)

        self.assertTrue(self.obj.has_results())

        cumulative = self.obj.engine.aggregator.cumulative
        self.assertEqual("java.lang.RuntimeException: 123", cumulative[''][KPISet.ERRORS][0]['msg'])
        self.assertEqual(1, cumulative[''][KPISet.SUCCESSES])

    def test_load_mode(self):
        self.obj.engine.aggregator = ConsolidatingAggregator()
        self.obj.execution.merge({
            "iterations": 10,
            "scenario": {"script": RESOURCES_DIR + "selenium/invalid/SimpleTest.java"},
        })
        self.obj.settings.merge({"junit-version": 5})
        self.obj.prepare()
        self.obj.engine.aggregator.prepare()
        self.obj.startup()
        while not self.obj.check():
            time.sleep(self.obj.engine.check_interval)
        self.obj.shutdown()
        self.obj.post_process()
        self.obj.engine.aggregator.post_process()
        self.assertTrue(self.obj.has_results())
        self.assertTrue(self.obj.report_file.endswith(".csv"))
        self.assertIsInstance(self.obj.reader, JTLReader)

    def test_func_mode(self):
        self.obj.engine.aggregator = FunctionalAggregator()
        self.obj.execution.merge({
            "iterations": 10,
            "scenario": {"script": RESOURCES_DIR + "selenium/invalid/SimpleTest.java"},
        })
        self.obj.settings.merge({"junit-version": 5})
        self.obj.prepare()
        self.obj.engine.aggregator.prepare()
        self.obj.startup()
        while not self.obj.check():
            time.sleep(self.obj.engine.check_interval)
        self.obj.shutdown()
        self.obj.post_process()
        self.obj.engine.aggregator.post_process()

        self.obj.reader.report_reader.json_reader.file.close()

        self.assertTrue(self.obj.has_results())
        self.assertTrue(self.obj.report_file.endswith(".ldjson"))
        self.assertIsInstance(self.obj.reader, FuncSamplesReader)


