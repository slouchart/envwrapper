# -*- coding: UTF-8 -*-


from setuptools import setup, find_packages
import io


with io.open('README.txt') as f:
    readme = f.read()


setup(
    name="envwrapper",
    version="0.0.0",
    description='Environment variables made simple',
    long_description=readme,
    packages=find_packages(exclude=('tests*', )),
    author='Sébastien LOUCHART',
    author_email='sebastien.louchart@gmail.com',
    license='MIT',
    tests_require=['pytest', 'pytest-cov']
)
