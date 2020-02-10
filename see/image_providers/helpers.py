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

import hashlib
import os


def verify_checksum(path, checksum):
    hash_md5 = hashlib.md5()
    block_size = os.statvfs(path).f_bsize
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            hash_md5.update(chunk)
    return hash_md5.hexdigest() == checksum
