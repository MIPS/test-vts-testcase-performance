#!/usr/bin/env python
#
# Copyright (C) 2016 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging

from vts.runners.host import asserts
from vts.runners.host import base_test_with_webdb
from vts.runners.host import const
from vts.runners.host import test_runner
from vts.utils.python.controllers import android_device
from vts.utils.python.cpu import cpu_frequency_scaling


class BinderPerformanceTest(base_test_with_webdb.BaseTestWithWebDbClass):
    """A testcase for the Binder Performance Benchmarking.

    Attributes:
        dut: the target DUT (device under test) instance.
        _cpu_freq: CpuFrequencyScalingController instance of self.dut.
    """

    THRESHOLD = {
        32: {
            "4": 150000,
            "8": 150000,
            "16": 150000,
            "32": 150000,
            "64": 150000,
            "128": 150000,
            "256": 150000,
            "512": 150000,
            "1024": 150000,
            "2k": 200000,
            "4k": 300000,
            "8k": 400000,
            "16k": 600000,
            "32k": 800000,
            "64k": 1000000,
        },
        64: {
            "4": 150000,
            "8": 150000,
            "16": 150000,
            "32": 150000,
            "64": 150000,
            "128": 150000,
            "256": 150000,
            "512": 150000,
            "1024": 150000,
            "2k": 200000,
            "4k": 300000,
            "8k": 400000,
            "16k": 600000,
            "32k": 800000,
            "64k": 1000000,
        }
    }
    LABEL_PREFIX = "BM_sendVec_binder/"

    def setUpClass(self):
        self.dut = self.registerController(android_device)[0]
        self.dut.shell.InvokeTerminal("one")
        self.dut.shell.one.Execute("stop")
        self.dut.shell.one.Execute("setprop sys.boot_completed 0")
        self._cpu_freq = cpu_frequency_scaling.CpuFrequencyScalingController(self.dut)
        self._cpu_freq.DisableCpuScaling()

    def setUpTest(self):
        self._cpu_freq.SkipIfThermalThrottling(retry_delay_secs=30)

    def tearDownTest(self):
        self._cpu_freq.SkipIfThermalThrottling()

    def tearDownClass(self):
        self._cpu_freq.EnableCpuScaling()
        self.dut.shell.one.Execute("start")
        self.dut.waitForBootCompletion()

    def testRunBenchmark32Bit(self):
        """A testcase which runs the 32-bit benchmark."""
        self.RunBenchmark(32)

    def testRunBenchmark64Bit(self):
        """A testcase which runs the 64-bit benchmark."""
        self.RunBenchmark(64)

    def RunBenchmark(self, bits):
        """Runs the native binary and parses its result.

        Args:
            bits: integer (32 or 64), the number of bits in a word chosen
                  at the compile time (e.g., 32- vs. 64-bit library).
        """
        # Runs the benchmark.
        logging.info("Start to run the benchmark (%s bit mode)", bits)
        binary = "/data/local/tmp/%s/libbinder_benchmark%s" % (bits, bits)

        results = self.dut.shell.one.Execute([
            "chmod 755 %s" % binary, "LD_LIBRARY_PATH=/data/local/tmp/%s/hw:"
            "/data/local/tmp/%s:"
            "$LD_LIBRARY_PATH %s" % (bits, bits, binary)
        ])

        # Parses the result.
        asserts.assertEqual(len(results[const.STDOUT]), 2)
        asserts.assertFalse(
            any(results[const.EXIT_CODE]),
            "BinderPerformanceTest failed.")
        logging.info("stderr: %s", results[const.STDERR][1])
        stdout_lines = results[const.STDOUT][1].split("\n")
        logging.info("stdout: %s", stdout_lines)
        label_result = []
        value_result = []
        for line in stdout_lines:
            if line.startswith(self.LABEL_PREFIX):
                tokens = line.split()
                benchmark_name = tokens[0]
                time_in_ns = tokens[1].split()[0]
                logging.info(benchmark_name)
                logging.info(time_in_ns)
                label_result.append(
                    benchmark_name.replace(self.LABEL_PREFIX, ""))
                value_result.append(int(time_in_ns))

        logging.info("result label for %sbits: %s", bits, label_result)
        logging.info("result value for %sbits: %s", bits, value_result)
        # To upload to the web DB.
        self.AddProfilingDataLabeledVector(
            "binder_vector_roundtrip_latency_benchmark_%sbits" % bits,
            label_result,
            value_result,
            x_axis_label="Message Size (Bytes)",
            y_axis_label="Roundtrip Binder RPC Latency (nanoseconds)")

        # Assertions to check the performance requirements
        for label, value in zip(label_result, value_result):
            if label in self.THRESHOLD[bits]:
                asserts.assertLess(
                    value, self.THRESHOLD[bits][label],
                    "%s ns for %s is longer than the threshold %s ns" % (
                        value, label, self.THRESHOLD[bits][label]))


if __name__ == "__main__":
    test_runner.main()
