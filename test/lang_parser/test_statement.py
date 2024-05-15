#!/usr/bin/env python3

import os
import subprocess

testcase_dir = os.path.realpath("/app/experiment_2/test/cases")
testcases = set([testcase[:testcase.rfind('.')] for testcase in os.listdir(testcase_dir)])

for testcase in testcases:
    path = testcase_dir + "/" + testcase
    print(f"Testing {testcase}...")
    print(f"Our Implementation")
    command = os.path.realpath("/app/experiment_2/src/lian/lang/main.py") + " --lang=ruby -debug -print_statements " + os.path.realpath(f"{path}.rb")
    os.system(command)