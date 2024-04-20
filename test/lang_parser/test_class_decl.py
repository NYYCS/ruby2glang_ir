#!/usr/bin/env python3

import os

command = os.path.realpath("/app/experiment_2/src/lian/lang/main.py") + " --lang=ruby -debug -print_statements " + os.path.realpath("/app/experiment_2/test/cases/var_decl.rb")

print(command)

os.system(command)