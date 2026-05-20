from setuptools import find_packages
from setuptools import setup

setup(
    name='amr_interfaces',
    version='0.0.1',
    packages=find_packages(
        include=('amr_interfaces', 'amr_interfaces.*')),
)
