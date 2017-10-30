# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""Unit tests for scancommand.py."""

# This file has tests for specific functions in rho.scancommand, but
# does not actually call ScanCommand.main(). The tests that do call
# main are in test_clicommand.py, becuase that's where the
# infrastructure for mocking out credentials and profiles is.

import unittest

from rho import scancommand


# pylint: disable=invalid-name
class TestScanCommand(unittest.TestCase):
    """Unit tests for scancommand.py."""

    def test_make_inventory_dict_one_host(self):
        """Test scancommand.make_inventory_dict with just one host."""

        auth = {
            'id': '1',
            'name': 'auth_1',
            'username': 'user',
            'password': 'pass',
            'ssh_key_file': 'sshkey'}
        self.assertEqual(
            scancommand.make_inventory_dict(
                ['host_ip_1'],           # success_hosts
                {'host_ip_1': '22'},     # success_port_map
                {'host_ip_1': [auth]}),  # auth_map
            {'alpha':
             {'hosts':
              {'host_ip_1':
               {'ansible_host': 'host_ip_1',
                'ansible_port': '22',
                'ansible_user': 'user',
                'ansible_ssh_pass': 'pass',
                'ansible_ssh_private_key_file': 'sshkey'}}}})
