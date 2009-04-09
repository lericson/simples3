#!/usr/bin/env python

from distutils.core import setup, Extension

import simples3
usage = "\nUsage\n-----\n\n" + simples3.__doc__
long_description = open("README", "U").read() + usage

setup(name="simples3", version="0.2",
      url="http://lericson.se/",
      author="Ludvig Ericson", author_email="ludvig@lericson.se",
      description="Simple, quick Amazon AWS S3 interface",
      long_description=long_description,
      py_modules=["simples3"])
