#!/usr/bin/env python3

import site
import sys
from distutils.core import setup

# workaround for https://github.com/pypa/pip/issues/7953
site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

setup(
	name="fmtlua",
	version="0.1",
	description="Lua source formatter",
	author="Tim Marston",
	author_email="tim@ed.am",
	url="https://ed.am/dev/",
	package_dir={"": "src"},
	packages=["fmtlua"],
	scripts=["fmtlua"],
)
