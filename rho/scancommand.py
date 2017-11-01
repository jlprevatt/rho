#
# Copyright (c) 2009-2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
# pylint: disable=too-few-public-methods, too-many-lines

""" Rho CLI Commands """

from __future__ import print_function
import os
import sys
import time
from tempfile import NamedTemporaryFile
from rho import utilities
from rho.clicommand import CliCommand
from rho.vault import get_vault_and_password
from rho.utilities import (
    multi_arg, _read_in_file, iteritems,
    PROFILE_HOSTS_SUFIX,
    PROFILE_HOST_AUTH_MAPPING_SUFFIX
)
from rho import host_discovery
from rho import inventory_scan
from rho import facts
from rho.translation import _


def redacted_auth_string(auth):
    """Format an auth for the host auth mapping file.

    :param auth: the auth. A dictionary with fields 'id', 'name',
        'username', 'password', and 'ssh_key_file'.

    :returns: a string of the form
      'name, username, ********, ssh_key_file'
    """

    name = auth.get('name')
    username = auth.get('username')
    ssh_key_file = auth.get('ssh_key_file')

    return '{0}, {1}, {2}, {3}'.format(
        name, username, utilities.PASSWORD_MASKING, ssh_key_file)


# Helper function to create a file to store the mapping
# between hosts and ALL the auths that were ever succesful
# with them arranged according to profile and date of scan.
def _create_hosts_auths_file(success_auth_map, profile):
    host_auth_mapping = profile + PROFILE_HOST_AUTH_MAPPING_SUFFIX
    host_auth_mapping_path = utilities.get_config_path(host_auth_mapping)
    with open(host_auth_mapping_path, 'a') as host_auth_file:
        string_to_write = time.strftime("%c") + '\n-' \
                                                '---' \
                                                '---' \
                                                '---' \
                                                '---' \
                                                '---' \
                                                '---' \
                                                '---' \
                                                '---' \
                                                '---' \
                                                '---\n'
        for host, line in iteritems(success_auth_map):
            string_to_write += host + '\n----------------------\n'
            for auth in line:
                string_to_write += redacted_auth_string(auth)
            string_to_write += '\n\n'
        string_to_write += '\n*******************************' \
                           '*********************************' \
                           '**************\n\n'
        host_auth_file.write(string_to_write)


class ScanCommand(CliCommand):
    """ The command that performs the scanning and collection of
    facts by making the playbook, inventory and running ansible.
    """

    def __init__(self):
        usage = _("usage: %prog scan [options] PROFILE")
        shortdesc = _("scan given host profile")
        desc = _("scans the host profile")

        CliCommand.__init__(self, "scan", usage, shortdesc, desc)

        self.parser.add_option("--cache", dest="cache", action="store_true",
                               metavar="RESET", default=False,
                               help=_("Use if profiles/auths previously "
                                      "discovered should be reused"))

        self.parser.add_option("--profile", dest="profile", metavar="PROFILE",
                               help=_("NAME of the profile - REQUIRED"))

        self.parser.add_option("--reportfile", dest="report_path",
                               metavar="REPORTFILE",
                               help=_("Report file path - REQUIRED"))

        self.parser.add_option("--facts", dest="facts", metavar="FACTS",
                               action="callback", callback=multi_arg,
                               default=[], help=_("'default', list or file"))

        self.parser.add_option("--scan-dirs", dest="scan_dirs",
                               metavar="SCANDIRS", action="callback",
                               callback=multi_arg, default=[],
                               help=_("list of remote directories to scan"))

        self.parser.add_option("--ansible-forks", dest="ansible_forks",
                               metavar="FORKS",
                               help=_("number of ansible forks"))

        self.parser.add_option("--vault", dest="vaultfile", metavar="VAULT",
                               help=_("file containing vault password for"
                                      " scripting"))

        self.parser.add_option("--logfile", dest="logfile", metavar="LOGFILE",
                               help=_("file to log scan output to"))

        self.facts_to_collect = None

    # pylint: disable=too-many-branches
    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.profile:
            print(_("No profile specified."))
            self.parser.print_help()
            sys.exit(1)

        if not self.options.report_path:
            print(_("No report location specified."))
            self.parser.print_help()
            sys.exit(1)

        if self.options.ansible_forks:
            try:
                if int(self.options.ansible_forks) <= 0:
                    print(_("--ansible-forks can only be a positive integer."))
                    self.parser.print_help()
                    sys.exit(1)
            except ValueError:
                print(_("--ansible-forks can only be a positive integer."))
                self.parser.print_help()
                sys.exit(1)

        # perform fact validation
        input_facts = self.options.facts
        assert isinstance(input_facts, list)

        if input_facts and os.path.isfile(input_facts[0]):
            input_facts = _read_in_file(input_facts[0])

        self.facts_to_collect = facts.expand_facts(input_facts)

        if self.options.scan_dirs == []:
            self.options.scan_dirs = ['/', '/opt', '/app', '/home', '/usr']
        elif os.path.isfile(self.options.scan_dirs[0]):
            self.options.scan_dirs = \
                _read_in_file(self.options.scan_dirs[0])
        else:
            assert isinstance(self.options.scan_dirs, list)
        # check that all values in scan_dirs are valid abs paths
        invalid_paths = utilities.check_path_validity(self.options.scan_dirs)
        if invalid_paths != []:
            print(_("Invalid paths were supplied to the --scan-dirs option: " +
                    ",".join(invalid_paths)))
            self.parser.print_help()
            sys.exit(1)

    # pylint: disable=too-many-statements
    def _do_command(self):
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        vault, vault_pass = get_vault_and_password(self.options.vaultfile)
        profile_found = False
        profile_auth_list = []
        profile_ranges = []
        profile_port = 22
        profile = self.options.profile
        forks = self.options.ansible_forks \
            if self.options.ansible_forks else '50'
        report_path = os.path.abspath(os.path.normpath(
            self.options.report_path))
        hosts_yml = profile + PROFILE_HOSTS_SUFIX
        hosts_yml_path = utilities.get_config_path(hosts_yml)

        # Checks if profile exists and stores information
        # about that profile for later use.
        if not os.path.isfile(utilities.PROFILES_PATH):
            print(_('No profiles exist yet.'))
            sys.exit(1)

        if not os.path.isfile(utilities.CREDENTIALS_PATH):
            print(_('No auth credentials exist yet.'))
            sys.exit(1)

        profiles_list = vault.load_as_json(utilities.PROFILES_PATH)
        for curr_profile in profiles_list:
            if self.options.profile == curr_profile.get('name'):
                profile_found = True
                profile_ranges = curr_profile.get('hosts')
                profile_auths = curr_profile.get('auth')
                profile_port = curr_profile.get('ssh_port')
                cred_list = vault.load_as_json(utilities.CREDENTIALS_PATH)
                for auth in profile_auths:
                    for cred in cred_list:
                        if auth.get('id') == cred.get('id'):
                            profile_auth_list.append(cred)
                break

        if not profile_found:
            print(_("Invalid profile. Create profile first"))
            sys.exit(1)

        # cache is used when the profile/auth mapping has been previously
        # used and does not need to be rerun.
        if not self.options.cache:
            success_hosts = []
            success_port_map = {}
            auth_map = {}
            remaining_hosts = profile_ranges
            cred_names = [cred.get('name') for cred in profile_auth_list]
            creds_str = ', '.join(cred_names)
            print(_('Connection discovery will be perform with the following'
                    ' auth credentials: %s' % (creds_str)))
            print(_('Note: Any ssh-agent connection setup for a target host '
                    'will be used as a fallback if it exists.'))
            print()
            for cred_item in profile_auth_list:
                success_hosts_, success_port_map_, \
                    auth_map_, remaining_hosts_ = \
                    host_discovery.create_ping_inventory(
                        vault, vault_pass,
                        remaining_hosts,
                        profile_port,
                        cred_item, forks,
                        self.verbosity)
                success_hosts = success_hosts + success_hosts_
                remaining_hosts = remaining_hosts_
                success_port_map.update(success_port_map_)
                auth_map.update(auth_map_)
            if not success_hosts:
                print(_('All auths are invalid for this profile'))
                sys.exit(1)

            num_success = len(success_hosts)
            num_failed = len(remaining_hosts)
            num_total = num_success + num_failed
            if num_failed > 0:
                with NamedTemporaryFile(mode='w', delete=False) as failed_temp:
                    for failed in remaining_hosts:
                        failed_temp.write(failed + '\n')
                    print(_('Failed to connect to %d systems with all auth '
                            'credentials. See the following file "%s" for a '
                            'list  of the failed systems.' %
                            (num_failed, failed_temp.name)))
                if self.verbosity:
                    failed_hosts = ', '.join(remaining_hosts)
                    print(_('Failed to connect to the following systems: %s.'
                            % (failed_hosts)))
                print()

            print(_('Scan will be performed against %d of %d systems.' %
                    (num_success, num_total)))
            print()

            _create_hosts_auths_file(auth_map, profile)

            inventory_scan.create_main_inventory(vault, success_hosts,
                                                 success_port_map, auth_map,
                                                 hosts_yml_path)

        elif os.path.isfile(hosts_yml_path):
            print("Profile '" + profile + "' has not been processed. " +
                  "Please run without using --cache with the profile first.")
            sys.exit(1)

        scan_succeeded = inventory_scan.inventory_scan(
            hosts_yml_path, self.facts_to_collect, report_path, vault_pass,
            profile, forks=forks, scan_dirs=self.options.scan_dirs,
            log_path=self.options.logfile,
            verbosity=self.verbosity)

        if scan_succeeded:
            host_auth_mapping = \
                self.options.profile + PROFILE_HOST_AUTH_MAPPING_SUFFIX
            host_auth_mapping_path = \
                utilities.get_config_path(host_auth_mapping)
            print(_("Scanning has completed. The mapping has been"
                    " stored in file '" + host_auth_mapping_path +
                    "'. The facts have been stored in '" +
                    report_path + "'"))
        else:
            print(_("An error has occurred during the scan. Please review" +
                    " the output to resolve the given issue."))
            sys.exit(1)
