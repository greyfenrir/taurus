import json
import os

import time

import apiritif
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from bzt.engine import EXEC
from bzt.modules import ConsolidatingAggregator
from bzt.modules.functional import FuncSamplesReader, LoadSamplesReader, FunctionalAggregator
from bzt.modules.apiritif import ApiritifNoseExecutor
from bzt.modules.pytest import PyTestExecutor
from bzt.modules.robot import RobotExecutor
from tests import RESOURCES_DIR, ExecutorTestCase, BZTestCase
from tests.modules.selenium import SeleniumTestCase
from bzt.resources.selenium_extras import Manager


class MockWebDriver(object):
    def __init__(self, content, timeout=60):
        self.content = []
        for element in content:
            key, val = list(element.items())[0]
            self.content.append((Manager.BYS[key.lower()], val))
        self.timeout = timeout
        self.waiting_time = 0

    def implicitly_wait(self, timeout):
        self.timeout = timeout

    def find_elements(self, *target):
        self.waiting_time += self.timeout
        return [element for element in self.content if element == target]


class TestRobotExecutor(ExecutorTestCase):
    EXECUTOR = RobotExecutor

    def test_full_single_script(self):
        self.configure({
            "execution": [{
                "scenario": {
                    "script": RESOURCES_DIR + "selenium/robot/simple/test.robot"
                }
            }]
        })
        self.obj.prepare()
        try:
            self.obj.startup()
            while not self.obj.check():
                time.sleep(self.obj.engine.check_interval)
        finally:
            self.obj.shutdown()
        self.obj.post_process()
        self.assertFalse(self.obj.has_results())
        self.assertNotEquals(self.obj.process, None)
        lines = open(self.obj.report_file).readlines()
        self.assertEqual(5, len(lines))

        self.assertIsNotNone(self.obj.output_file)
        self.assertIsNotNone(self.obj.log_file)

    def test_hold(self):
        self.configure({
            "execution": [{
                "hold-for": "5s",
                "scenario": {
                    "script": RESOURCES_DIR + "selenium/robot/simple/test.robot"
                }
            }]
        })
        self.obj.prepare()
        try:
            start_time = time.time()
            self.obj.startup()
            while not self.obj.check():
                time.sleep(self.obj.engine.check_interval)
        finally:
            self.obj.shutdown()
        self.obj.post_process()
        self.assertTrue(os.path.exists(self.obj.report_file))
        duration = time.time() - start_time
        self.assertGreater(duration, 5)

    def test_iterations(self):
        self.configure({
            "execution": [{
                "iterations": 3,
                "scenario": {
                    "script": RESOURCES_DIR + "selenium/robot/simple/test.robot"
                }
            }]
        })
        self.obj.prepare()
        try:
            self.obj.startup()
            while not self.obj.check():
                time.sleep(self.obj.engine.check_interval)
        finally:
            self.obj.shutdown()
        self.obj.post_process()
        self.assertFalse(self.obj.has_results())
        self.assertNotEquals(self.obj.process, None)
        lines = open(self.obj.report_file).readlines()
        self.assertEqual(3 * 5, len(lines))

    def test_variables(self):
        self.configure({
            "execution": [{
                "iterations": 1,
                "scenario": {
                    "variables": {
                        "USERNAME": "janedoe",
                    },
                    "script": RESOURCES_DIR + "selenium/robot/simple/test_novar.robot",
                }
            }]
        })
        self.obj.prepare()
        try:
            self.obj.startup()
            while not self.obj.check():
                time.sleep(self.obj.engine.check_interval)
        finally:
            self.obj.shutdown()
        self.obj.post_process()
        self.assertFalse(self.obj.has_results())
        self.assertNotEquals(self.obj.process, None)
        samples = [json.loads(line) for line in open(self.obj.report_file).readlines() if line]
        self.obj.log.info(samples)
        self.assertEqual(5, len(samples))
        self.assertTrue(all(sample["status"] == "PASSED" for sample in samples))

    def test_variables_file(self):
        self.configure({
            "execution": [{
                "iterations": 1,
                "scenario": {
                    "variables": RESOURCES_DIR + "selenium/robot/simple/vars.yaml",
                    "script": RESOURCES_DIR + "selenium/robot/simple/test_novar.robot",
                }
            }]
        })
        self.obj.prepare()
        try:
            self.obj.startup()
            while not self.obj.check():
                time.sleep(self.obj.engine.check_interval)
        finally:
            self.obj.shutdown()
        self.obj.post_process()
        self.assertFalse(self.obj.has_results())
        self.assertNotEquals(self.obj.process, None)
        samples = [json.loads(line) for line in open(self.obj.report_file).readlines() if line]
        self.obj.log.info(samples)
        self.assertEqual(5, len(samples))
        self.assertTrue(all(sample["status"] == "PASSED" for sample in samples))

    def test_single_tag(self):
        self.configure({
            "execution": [{
                "iterations": 1,
                "scenario": {
                    "tags": "create",
                    "script": RESOURCES_DIR + "selenium/robot/simple/test.robot",
                }
            }]
        })
        self.obj.prepare()
        try:
            self.obj.startup()
            while not self.obj.check():
                time.sleep(self.obj.engine.check_interval)
        finally:
            self.obj.shutdown()
        self.obj.post_process()
        self.assertFalse(self.obj.has_results())
        self.assertNotEquals(self.obj.process, None)
        samples = [json.loads(line) for line in open(self.obj.report_file).readlines() if line]
        self.obj.log.info(samples)
        self.assertEqual(1, len(samples))
        self.assertTrue(all(sample["status"] == "PASSED" for sample in samples))

    def test_multiple_tags(self):
        self.configure({
            "execution": [{
                "iterations": 1,
                "scenario": {
                    "tags": "create,database",
                    "script": RESOURCES_DIR + "selenium/robot/simple/test.robot",
                }
            }]
        })
        self.obj.prepare()
        try:
            self.obj.startup()
            while not self.obj.check():
                time.sleep(self.obj.engine.check_interval)
        finally:
            self.obj.shutdown()
        self.obj.post_process()
        self.assertFalse(self.obj.has_results())
        self.assertNotEquals(self.obj.process, None)
        samples = [json.loads(line) for line in open(self.obj.report_file).readlines() if line]
        self.obj.log.info(samples)
        self.assertEqual(2, len(samples))
        self.assertTrue(all(sample["status"] == "PASSED" for sample in samples))
