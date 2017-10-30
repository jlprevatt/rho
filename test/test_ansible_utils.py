# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""Tests for rho/scancommand.py. logging"""

import unittest

from rho import ansible_utils
from rho import utilities


# pylint: disable=invalid-name, unused-argument, missing-docstring
class TestScanCommandLogging(unittest.TestCase):
    """Tests for rho/scancommand.py logging"""

    def test_redact_dict(self):
        keys = ['key1']
        a_dict = {
            'key1': 'val1',
            'key2': 'val2'
        }
        self.assertEqual(
            ansible_utils.redact_dict(keys, a_dict),
            {
                'key1': utilities.PASSWORD_MASKING,
                'key2': 'val2'
            })

    def test_log_yaml_inventory(self):

        inventory = {
            'alpha': {
                'hosts': {
                    'host1': {
                        'ansible_become_pass': 'sudo_password',
                        'ansible_port': 22
                    }
                },
                'vars': {
                    'ansible_ssh_pass': 'ssh_password',
                    'ansible_user': 'root'
                }
            }
        }
        self.assertEqual(
            ansible_utils.log_yaml_inventory('out message', inventory),
            {
                'alpha': {
                    'hosts': {
                        'host1': {
                            'ansible_become_pass': utilities.PASSWORD_MASKING,
                            'ansible_port': 22
                        }
                    },
                    'vars': {
                        'ansible_ssh_pass': utilities.PASSWORD_MASKING,
                        'ansible_user': 'root'
                    }
                }
            }
        )
