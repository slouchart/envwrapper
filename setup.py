# -*- coding: UTF-8 -*-


from setuptools import setup, find_packages
import io


with io.open('README.md') as f:
    readme = f.read()


setup(
    name="envwrapper",
    version="0.1",
    description='Environment variables for mere developers',
    long_description=readme,
    packages=find_packages(exclude=('tests*', )),
    author='Sébastien LOUCHART',
    author_email='sebastien.louchart@gmail.com',
    license='MIT',
    tests_require=['pytest', 'pytest-cov'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development',
        'Topic :: Utilities'
    ]
)
