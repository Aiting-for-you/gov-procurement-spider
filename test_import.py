# test_import.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import importlib

try:
    parser_module_name = "detail_parsers.guangdong"
    parser_module = importlib.import_module(parser_module_name)
    print(f"Successfully imported {parser_module_name}")
except ImportError as e:
    print(f"Failed to import {parser_module_name}: {e}") 