# Copyright 2015-2017 F-Secure

# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You may
# obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

import os
import sys
from setuptools import setup, find_packages

required_packages = ['libvirt-python']

# Python < 3.3 requires backported ipaddress package
major_version, minor_version = sys.version_info[:2]
if major_version < 3 or minor_version < 3:
    required_packages.append('ipaddress')


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="python-see",
    version="1.2.6",
    author="F-Secure Corporation",
    author_email="matteo.cafasso@f-secure.com",
    description=("Sandboxed Execution Environment"),
    license="Apache License 2.0",
    packages=find_packages(),
    install_requires=required_packages,
    keywords="sandbox test automation",
    url="https://github.com/f-secure/see",
    long_description=read('README.rst'),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
)
