#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import re

import sqlalchemy


_SQLA_VERSION = tuple(
    int(num) if re.match(r'^\d+$', num) else num
    for num in sqlalchemy.__version__.split(".")
)

sqla_097 = _SQLA_VERSION >= (0, 9, 7)
sqla_094 = _SQLA_VERSION >= (0, 9, 4)
sqla_090 = _SQLA_VERSION >= (0, 9, 0)
sqla_08 = _SQLA_VERSION >= (0, 8)
