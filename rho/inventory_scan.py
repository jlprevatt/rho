# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""Scan for software on hosts in an inventory."""

from __future__ import print_function

import csv
import json
import os.path
import sys
import tempfile
import time

from rho import ansible_utils, postprocessing, utilities
from rho.translation import _ as t
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


# pylint: disable=too-many-arguments, too-many-statements
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

    variables_path = os.path.join(
        tempfile.gettempdir(),
        'rho-fact-temp-' + str(time.time()))

    ansible_vars = {'facts_to_collect': list(facts_to_collect),
                    'report_path': report_path,
                    'scan_dirs': ' '.join(scan_dirs or []),
                    'variables_path': variables_path}

    if os.path.isfile(utilities.PLAYBOOK_DEV_PATH):
        playbook = utilities.PLAYBOOK_DEV_PATH
    elif os.path.isfile(utilities.PLAYBOOK_RPM_PATH):
        playbook = utilities.PLAYBOOK_RPM_PATH
    else:
        print(t("rho scan playbook not found locally or in '%s'")
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

    try:
        ansible_utils.run_with_vault(
            cmd_string, vault_pass,
            log_path=log_path,
            log_to_stdout=True,
            ansible_verbosity=verbosity,
            print_before_run=True)
    except ansible_utils.AnsibleProcessException as ex:
        print(t("An error has occurred during the scan. Please review" +
                " the output to resolve the given issue: %s" % str(ex)))
        sys.exit(1)

    with open(variables_path, 'r') as variables_file:
        vars_by_host = json.load(variables_file)

    # Postprocess Ansible output
    facts_out = []
    for _, host_vars in utilities.iteritems(vars_by_host):
        this_host = {}

        this_host.update(host_vars['connection'])
        this_host.update(host_vars['cpu'])
        this_host.update(host_vars['date'])
        this_host.update(host_vars['dmi'])
        this_host.update(host_vars['etc_release'])
        this_host.update(host_vars['file_contents'])
        this_host.update(host_vars['redhat_packages'])
        this_host.update(host_vars['redhat_release'])
        this_host.update(host_vars['subman'])
        this_host.update(host_vars['uname'])
        this_host.update(host_vars['virt'])
        this_host.update(host_vars['virt_what'])

        this_host.update(
            postprocessing.process_jboss_versions(facts_to_collect, host_vars))
        this_host.update(
            postprocessing.process_addon_versions(facts_to_collect, host_vars))
        this_host.update(
            postprocessing.process_id_u_jboss(facts_to_collect, host_vars))
        this_host.update(
            postprocessing.process_jboss_eap_common_files(
                facts_to_collect, host_vars))
        this_host.update(
            postprocessing.process_jboss_eap_processes(
                facts_to_collect, host_vars))
        this_host.update(
            postprocessing.process_jboss_eap_packages(
                facts_to_collect, host_vars))
        this_host.update(
            postprocessing.process_jboss_eap_locate(
                facts_to_collect, host_vars))
        this_host.update(
            postprocessing.process_jboss_eap_init_files(
                facts_to_collect, host_vars))
        this_host.update(
            postprocessing.process_jboss_eap_home(facts_to_collect, host_vars))
        this_host.update(
            postprocessing.process_fuse_on_eap(facts_to_collect, host_vars))

        postprocessing.handle_systemid(facts_to_collect, this_host)
        postprocessing.handle_redhat_packages(facts_to_collect, this_host)
        postprocessing.escape_characters(this_host)

        facts_out.append(this_host)

    normalized_path = os.path.normpath(report_path)
    with open(normalized_path, 'w') as write_file:
        # Construct the CSV writer
        writer = csv.DictWriter(
            write_file, sorted(facts_to_collect), delimiter=',')

        # Write a CSV header if necessary
        file_size = os.path.getsize(normalized_path)
        if file_size == 0:
            # handle Python 2.6 not having writeheader method
            if sys.version_info[0] == 2 and sys.version_info[1] <= 6:
                headers = {}
                for fields in writer.fieldnames:
                    headers[fields] = fields
                writer.writerow(headers)
            else:
                writer.writeheader()

        # Write the data
        for data in facts_out:
            writer.writerow(data)
