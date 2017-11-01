# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""Scan for software on hosts in an inventory."""

import json
import os.path
import sys

from rho import ansible_utils, utilities
from rho.translation import _
from rho.utilities import str_to_ascii


# Creates the filtered main inventory on which the custom
# modules to collect facts are run. This inventory can be
# used multiple times later after a profile has first been
# processed and the valid mapping as been figured out by
# pinging.
# pylint: disable=too-many-locals
def make_inventory_dict(hosts, port_map, auth_map):
    """Make the inventory for the scan, as a dict.

    :param hosts: a list of hosts for the inventory
    :param port_map: mapping from hosts to SSH ports
    :param auth_map: map from host IP to a list of auths it works with

    :returns: a dict with the structure:

        .. code-block:: python

            {'alpha':
                {'hosts':
                    {'IP address 1': {'host-vars-1'},
                     'IP address 2': {'host-vars-2'},
                     # ...
                    }
                }
            }
    """

    yml_dict = {}

    # Create section of successfully connected hosts
    alpha_hosts = {}
    for host in hosts:
        ascii_host = str_to_ascii(host)
        ascii_port = str_to_ascii(str(port_map[host]))
        host_vars = {'ansible_host': ascii_host,
                     'ansible_port': ascii_port}
        host_vars.update(
            ansible_utils.auth_as_ansible_host_vars(auth_map[host][0]))
        alpha_hosts[ascii_host] = host_vars

    yml_dict['alpha'] = {'hosts': alpha_hosts}

    return yml_dict


def create_main_inventory(vault, hosts, port_map, auth_map, path):
    """Write an inventory file given the results of host discovery.

    :param vault: an Ansible vault to encrypt the results.
    :param hosts: a list of hosts in the inventory.
    :param port_map: a mapping from hosts to SSH port numbers.
    :param auth_map: a mapping from hosts to SSH credentials.
    :param path: the path to write the inventory.
    """

    yml_dict = make_inventory_dict(hosts, port_map, auth_map)
    vault.dump_as_yaml_to_file(yml_dict, path)
    ansible_utils.log_yaml_inventory('Main inventory', yml_dict)


# pylint: disable=too-many-arguments
def inventory_scan(hosts_yml_path, facts_to_collect, report_path,
                   vault_pass, base_name, forks=None,
                   scan_dirs=None, log_path=None, verbosity=0):
    """Run an inventory scan.

    :param hosts_yml_path: path to an Ansible inventory file to scan.
    :param facts_to_collect: a list of facts to collect.
    :param report_path: the path to write a report to.
    :param vault_pass: the vault password used to protect user data
    :param base_name: the base name of the output files
    :param forks: the number of Ansible forks, or None for default.
    :param scan_dirs: the directories on the remote host to scan, or None for
        default.
    :param log_path: path to log to, or None for default.
    :param verbosity: number of v's of Ansible verbosity.

    :returns: True if scan completed successfully, False if not.
    """

    hosts_yml = base_name + utilities.PROFILE_HOSTS_SUFIX
    hosts_yml_path = utilities.get_config_path(hosts_yml)

    ansible_vars = {'facts_to_collect': list(facts_to_collect),
                    'report_path': report_path,
                    'scan_dirs': ' '.join(scan_dirs or [])}

    if os.path.isfile(utilities.PLAYBOOK_DEV_PATH):
        playbook = utilities.PLAYBOOK_DEV_PATH
    elif os.path.isfile(utilities.PLAYBOOK_RPM_PATH):
        playbook = utilities.PLAYBOOK_RPM_PATH
    else:
        print(_("rho scan playbook not found locally or in '%s'")
              % playbook)
        sys.exit(1)

    cmd_string = ('ansible-playbook {playbook} '
                  '-i {inventory} -f {forks} '
                  '--ask-vault-pass '
                  '--extra-vars \'{vars}\'').format(
                      playbook=playbook,
                      inventory=hosts_yml_path,
                      forks=forks,
                      vars=json.dumps(ansible_vars))

    log_path = log_path or utilities.SCAN_LOG_PATH

    print('Running:', cmd_string)

    process = ansible_utils.run_with_vault(
        cmd_string, vault_pass,
        log_path=log_path,
        log_to_stdout=True,
        ansible_verbosity=verbosity)

    return process.exitstatus == 0 and process.signalstatus is None
