# Copyright 2015-2016 F-Secure

# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You may
# obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

from setuptools import setup, find_packages

setup(
    name="python-see",
    version="1.0.1",
    author="F-Secure Corporation",
    author_email="matteo.cafasso@f-secure.com",
    description=("Sandboxed Execution Environment"),
    license="Apache License 2.0",
    packages=find_packages(),
    install_requires=[
        'libvirt-python',
    ],
    keywords="sandbox test automation",
    url="https://github.com/f-secure/see",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
)
