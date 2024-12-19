import os
import sys
import shutil
from setuptools import setup, find_packages, find_namespace_packages
from setuptools.command.install import install

setup(name='astroscrape',
      version='1.0.0',
      description='scrape astronomy paper text from arXiv',
      author='David Nidever',
      author_email='dnidever@montana.edu',
      url='https://github.com/dnidever/astroscrape',
      requires=['numpy','astropy(>=4.0)','scipy'],
      zip_safe = False,
      include_package_data=True,
      packages=find_namespace_packages(where="python"),
      package_dir={"": "python"}
)
