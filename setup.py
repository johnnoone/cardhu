#!/usr/bin/env python

from setuptools import setup
from cardhu.util import cfg_to_args

setup(
    **cfg_to_args()
)
