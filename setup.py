#!/usr/bin/env python

from setuptools import setup
from cardhu.util import cfg_to_args

setup(
    include_package_data=True,
    **cfg_to_args()
)
