# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""Unit tests for host_discovery.py"""

import unittest

from rho import host_discovery


class TestProcessPingOutput(unittest.TestCase):
    """Unit tests for host_discovery.py"""

    def test_process_ping_output(self):
        """The output of a three-host scan"""
        success, failed = host_discovery.process_ping_output([
            '192.168.50.11 | SUCCESS | rc=0 >>',
            'Hello',
            '192.168.50.12 | SUCCESS | rc=0 >>',
            'Hello',
            '192.168.50.10 | SUCCESS | rc=0 >>',
            'Hello'])
        self.assertEqual(success,
                         set(['192.168.50.10',
                              '192.168.50.11',
                              '192.168.50.12']))
        self.assertEqual(failed, set())

    def test_process_ping_output_fail(self):
        """The output of a three-host scan"""
        success, failed = host_discovery.process_ping_output([
            '192.168.50.11 | UNREACHABLE! => {',
            '     "changed": false,',
            '     "msg": "Failed to connect to the host via ssh ...",',
            '     "unreachable": true',
            '    }',
            'Hello',
            '192.168.50.12 | SUCCESS | rc=0 >>',
            'Hello',
            '192.168.50.10 | SUCCESS | rc=0 >>',
            'Hello'])
        self.assertEqual(success,
                         set(['192.168.50.10',
                              '192.168.50.12']))
        self.assertEqual(failed, set(['192.168.50.11']))
