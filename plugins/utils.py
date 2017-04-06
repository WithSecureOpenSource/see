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

"""Common utility functions."""

import os
import subprocess


def launch_process(*args):
    return subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)


def collect_process_output(process, filename=None):
    output = process.communicate()[0].decode('utf8')

    if process.returncode == 0:
        if filename is not None:
            with open(filename, 'w') as result_file:
                result_file.write(output)
    else:
        raise RuntimeError(
            "%s exit code %d, output:\n%s"
            % (' '.join(process.args), process.returncode, output))


def create_folder(folder_path):
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
        except EnvironmentError:  # another hook created the same folder
            pass
