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

import xml.etree.ElementTree as etree


def subelement(element, xpath, tag, text, **kwargs):
    """
    Searches element matching the *xpath* in *parent* and replaces it's *tag*,
    *text* and *kwargs* attributes.

    If the element in *xpath* is not found a new child element is created
    with *kwargs* attributes and added.

    Returns the found/created element.
    """
    subelm = element.find(xpath)

    if subelm is None:
        subelm = etree.SubElement(element, tag)
    else:
        subelm.tag = tag

    subelm.text = text
    for attr, value in kwargs.items():
        subelm.set(attr, value)

    return subelm
