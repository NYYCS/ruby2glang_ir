#!/usr/bin/python3

import os

from tree_sitter import Language, Parser
from pathlib import Path

def obtain_lang_paths():
    ret_list = []
    langs = Path(LANGS_PATH).glob('*')
    for elem in langs:
        elem = str(elem)
        # if "typescript" in elem:
        #     elem = elem + "/typescript"
        if "php" in elem:
            elem = elem + "/php"
        ret_list.append(elem)
    return ret_list

PREFIX = "/app/experiment_2"
LANGS_PATH = PREFIX + "/scripts/tree-sitter-langs"
SO_PATH = PREFIX + "/lib/langs.so"

os.system("mkdir -p %s" % os.path.dirname(SO_PATH))
os.system("rm -f %s" % SO_PATH)

print("Building tree sitter grammar files...")
Language.build_library(SO_PATH, obtain_lang_paths())

Language(SO_PATH, 'go')
Language(SO_PATH, 'java')
Language(SO_PATH, 'rust')
Language(SO_PATH, 'cpp')
Language(SO_PATH, 'javascript')
Language(SO_PATH, 'python')
Language(SO_PATH, 'c_sharp')
Language(SO_PATH, 'php')
Language(SO_PATH, 'kotlin')
Language(SO_PATH, 'llvm')
Language(SO_PATH, 'ql')
Language(SO_PATH, 'ruby')
Language(SO_PATH, 'rust')
Language(SO_PATH, 'smali')
Language(SO_PATH, 'typescript')

print("Successfully tested: %s" % SO_PATH)
