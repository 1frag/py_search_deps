import sys

from setuptools import setup

requires = ["stdlib-list"]
if sys.version_info < (3, 9):
    requires.append('graphlib-backport')

setup(
    name="py_search_deps",
    version="0.1.0",
    py_modules=["py_search_deps"],
    author="Aleksei Piskunov",
    author_email="piskunov.alesha@gmail.com",
    description="Tool for searching modules dependencies",
    install_requires=requires,
)
