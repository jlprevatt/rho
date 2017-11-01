# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""Utilities for wrapping Ansible."""

from __future__ import print_function

import time
import sys

from getpass import getpass
import pexpect
import yaml

from rho import utilities
from rho.utilities import log, ANSIBLE_LOG_PATH, str_to_ascii, iteritems


def auth_as_ansible_host_vars(auth):
    """Get the Ansible host vars that implement an auth.

    :param auth: the auth. A dictionary with fields 'id', 'name',
        'username', 'password', and 'ssh_key_file'.

    :returns: a dict that can be used as the host variables in an
        Ansible inventory.
    """

    username = auth.get('username')
    password = auth.get('password')
    ssh_key_file = auth.get('ssh_key_file')
    sudo_password = auth.get('sudo_password')

    ansible_vars = {}

    ansible_vars['ansible_user'] = str_to_ascii(username)
    if password:
        ansible_vars['ansible_ssh_pass'] = str_to_ascii(password)
    if ssh_key_file:
        ansible_vars['ansible_ssh_private_key_file'] = \
            str_to_ascii(ssh_key_file)
    if sudo_password:
        ansible_vars['ansible_become_pass'] = sudo_password

    return ansible_vars


def redact_dict(redact_key_list, a_dict):
    """Redact_values in a dictionary

    :param redact_key_list: keys in dictionary that value should be redacted
    :param a_dict: A dictionary to redact
    :returns: the redacted dictionary
    """
    for key in redact_key_list:
        if a_dict is not None and key in a_dict:
            a_dict[key] = utilities.PASSWORD_MASKING
    return a_dict


def log_yaml_inventory(label, inventory):
    """Log yaml inventory but mask passwords

    :param inventory: A dictionary of the ansible inventory
    """
    alpha = inventory.get('alpha')
    hosts_dict = alpha.get('hosts')
    vars_dict = alpha.get('vars')
    redact_key_list = ['ansible_become_pass', 'ansible_ssh_pass']

    # pylint: disable=unused-variable
    for host, host_dict in iteritems(hosts_dict):
        host_dict = redact_dict(redact_key_list, host_dict)

    vars_dict = redact_dict(redact_key_list, vars_dict)

    log.debug('%s:\n%s', label, yaml.dump(inventory))
    return inventory


# pylint: disable=too-many-arguments
def run_with_vault(cmd_string, vault_pass, env=None, log_path=None,
                   log_to_stdout=True, ansible_verbosity=0):
    """Runs ansible command allowing for password to be provided after
    process triggered.

    Returns after the process completes.

    :param cmd_string: the command to run.
    :param vault_pass: the password to the user's Ansible Vault.
    :param env: the environment to run the subprocess in.
    :param log_path: a path to write the process's log to. Defaults to
        'XDG_DATA_HOME/rho/ansible_log'.
    :param log_to_stdout: if True, write Ansible's log to stdout. Defaults to
        True.
    :param ansible_verbosity: the number of v's of Ansible verbosity.
    :returns: the popen.spawn object for the process.
    """

    # pexpect provides the ability to send the process's output to a
    # single Python file object. We want to send it to a file and
    # maybe also stdout. The solution is to have pexpect log to the
    # file and then use 'tail -f' to copy that to stdout.

    if not log_path:
        log_path = ANSIBLE_LOG_PATH

    if ansible_verbosity:
        cmd_string = cmd_string + ' -' + 'v' * ansible_verbosity

    try:
        utilities.ensure_data_dir_exists()
        with open(log_path, 'wb') as logfile:
            pass
        with open(log_path, 'r+b') as logfile:
            log.debug('Running Ansible: %s', cmd_string)
            child = pexpect.spawn(cmd_string, timeout=None,
                                  env=env)

            if log_to_stdout:
                utilities.threaded_tailing(log_path, ansible_verbosity)

            child.expect('Vault password:')
            child.sendline(vault_pass)
            # Set the log file *after* we send the user's Vault
            # password to Ansible, so we don't log the password.
            child.logfile = logfile
            last_pos = logfile.tell()

            i = child.expect([pexpect.EOF, 'Enter passphrase for key .*:',
                              'you want to continue connecting (yes/no)?'])
            while i:
                new_pos = logfile.tell()
                logfile.seek(last_pos)
                logfile_lines = logfile.readlines()
                log.info(logfile_lines)
                print(logfile_lines[-1].replace('\r\n', ''))
                logfile.seek(new_pos)
                last_pos = new_pos
                child.logfile = None
                # Ansible has already printed a prompt; it would be
                # confusing if getpass printed another one.
                child.sendline(getpass(''))
                child.logfile = logfile
                i = child.expect([pexpect.EOF, 'Enter passphrase for key .*:',
                                  'you want to continue connecting (yes/no)?'])

            if child.isalive():
                child.wait()
            if log_to_stdout:
                time.sleep(2)

        return child
    except pexpect.EOF:
        print('Error: unexpected Ansible output')
        sys.exit(1)
    except pexpect.TIMEOUT:
        print('Error: unexpected Ansible output')
        sys.exit(1)
