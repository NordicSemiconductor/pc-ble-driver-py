#
# Copyright (c) 2016 Nordic Semiconductor ASA
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
#   3. Neither the name of Nordic Semiconductor ASA nor the names of other
#   contributors to this software may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
#   4. This software must only be used in or with a processor manufactured by Nordic
#   Semiconductor ASA, or in or with a processor manufactured by a third party that
#   is used in combination with a processor manufactured by Nordic Semiconductor.
#
#   5. Any software provided in binary or object form under this license must not be
#   reverse engineered, decompiled, modified and/or disassembled.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""
Package marker file.

"""

__version__ = "0.16.0"





def clean_python_version():
    """
    On windows there is cross-contamination between python for the same versions of python
    but for x64 and x86. This sould remove the bad elements from path. 

    """
    import os 
    import sys
    import re
    # On the form Python3x-32 or Python3x depending on the architecture
    python_name = os.path.split(sys.prefix)[1]
    
    # The prefix should end in Python3x or Python3x-32
    pattern = re.compile("(Python3[0-9]+)(-32)?")
    match = (pattern.match(python_name) )
    if not match: 
        return
    prefix = match[1] # Python3x 
    suffix = match[2] # "" or "-32"
    inverse_suffix = { None :'-32', '-32' : ''}[suffix]
    bad_python = prefix + inverse_suffix 
    new_path = []
    for minipath in sys.path: 
        split_path = os.path.normpath(minipath).split(os.sep)
        if bad_python in split_path: 
            print("Bad element in python-path thrown out: " ,  minipath) 
        else: 
            new_path.append(minipath) 
    sys.path=new_path

clean_python_version()
