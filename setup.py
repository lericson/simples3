from distutils.core import setup, Extension

import simples3
long_description = """
`simples3` is a fairly simple, decently quick interface to Amazon's S3 storage
service.

It grew out of frustration with other libraries that were either written too
pragmatically (slow), too bloatedly, or just half-done.

The module aims for:

 * simplicity,
 * decent speed,
 * non-intrusiveness.

It really is designed to fit into programmer memory. The three basic operations
are as easy as with dictionaries.

Out of simplicity comes no dependencies - the code relies solely on Python
standard libraries.

The perhaps greatest setback is that it requires Python 2.5, nothing more,
nothing less.
""" + simples3.__doc__

setup(name="simples3", version="0.1",
      url="http://lericson.se/",
      author="Ludvig Ericson", author_email="ludvig@lericson.se",
      description="Simple, quick Amazon AWS S3 interface",
      long_description=long_description,
      py_modules=["simples3"])
