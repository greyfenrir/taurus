import json
import os
import shutil
import time
import traceback
from os import listdir
from os.path import exists, join, dirname

import yaml

from bzt.engine import EXEC
from bzt.modules.aggregator import ConsolidatingAggregator, KPISet
from bzt.modules.functional import FunctionalAggregator, FuncSamplesReader
from bzt.modules.java import JUnitTester, TestNGTester
from bzt.modules.java.executors import JavaTestRunner
from bzt.modules.java.tools import JavaC, JarTool, Hamcrest, SeleniumServer
from bzt.modules.jmeter import JTLReader
from bzt.modules.selenium import SeleniumExecutor
from bzt.utils import ToolError
from tests import BZTestCase, local_paths_config, RESOURCES_DIR, BUILD_DIR, ROOT_LOGGER, ExecutorTestCase
from tests.mocks import EngineEmul
from tests.modules.selenium import SeleniumTestCase


class TestTestNGTester(ExecutorTestCase):
    EXECUTOR = TestNGTester

    def setUp(self):
        super(TestTestNGTester, self).setUp()
        self.obj.engine.configure([local_paths_config()])
        self.obj.settings = self.obj.engine.config.get("modules").get("testng")

    def test_simple(self):
        self.obj.execution.merge({
            "scenario": {
                "script": RESOURCES_DIR + "selenium/testng/TestNGSuite.java"}})
        self.obj.settings['autodetect-xml'] = False
        self.obj.prepare()
        self.obj.startup()
        while not self.obj.check():
            time.sleep(self.obj.engine.check_interval)
        self.obj.shutdown()
        self.obj.post_process()

    def test_install_tools(self):
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
                "selenium-server": {
                    "path": join(installation_path, "selenium-server.jar"),
                    "download-link": source_url,
                    "version": "9.9"
                },
                "hamcrest-core": join(installation_path, "tools", "testng", "hamcrest-core.jar"),
                "path": JarTool.LOCAL_PATH})

            self.obj.execution.merge({
                "scenario": {
                    "script": RESOURCES_DIR + "selenium/testng/jars/testng-suite.jar"}})

            self.obj.prepare()

        finally:
            JarTool.URL = saved_url
            JarTool.LOCAL_PATH = saved_local_path

        self.assertTrue(isinstance(self.obj, TestNGTester))

        jar_tools = [tool for tool in self.obj._tools if isinstance(tool, JarTool)]
        self.assertTrue(15, len(jar_tools))

        for tool in jar_tools:
            msg = "Wrong path to {tool}: {path}".format(tool=str(tool), path=str(tool.tool_path))
            self.assertTrue(os.path.isfile(tool.tool_path), msg)
            if isinstance(tool, SeleniumServer):
                self.assertEqual(tool.version, "9.9.0")

    def test_failed_setup(self):
        self.obj.execution.merge({
            "scenario": {
                "script": RESOURCES_DIR + "selenium/testng/TestNGFailingSetup.java"}})
        self.obj.settings['autodetect-xml'] = False
        self.obj.prepare()
        self.obj.startup()
        while not self.obj.check():
            time.sleep(self.obj.engine.check_interval)
        self.obj.shutdown()
        self.obj.post_process()
        samples = [
            json.loads(line)
            for line in open(os.path.join(self.obj.engine.artifacts_dir, 'TestNGTester.ldjson')).readlines()
        ]
        self.assertEqual(samples[0]["status"], "FAILED")
        self.assertEqual(samples[1]["status"], "SKIPPED")


class TestJavaC(BZTestCase):
    def test_missed_tool(self):
        self.obj = JavaC()
        self.obj.tool_path = "javac-not-found"
        self.assertEqual(False, self.obj.check_if_installed())
        self.assertRaises(ToolError, self.obj.install)

    def test_get_version(self):
        self.obj = JavaC()
        out1 = "javac 10.0.1"
        out2 = "javac 1.8.0_151"

        self.assertEqual("10", self.obj._get_version(out1))
        self.assertEqual("8", self.obj._get_version(out2))


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


