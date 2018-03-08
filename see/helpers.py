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

import inspect


def lookup_class(fully_qualified_name):
    """
    Given its fully qualified name, finds the desired class and imports it.
    Returns the Class object if found.
    """
    module_name, class_name = str(fully_qualified_name).rsplit(".", 1)
    module = __import__(module_name, globals(), locals(), [class_name], 0)
    Class = getattr(module, class_name)

    if not inspect.isclass(Class):
        raise TypeError(
            "%s is not of type class: %s" % (class_name, type(Class)))

    return Class
