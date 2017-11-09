#
# Copyright (c) 2009-2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

""" A set of reusable methods common to many of the commands """

from __future__ import print_function
import csv
import logging
import os
import re
import sys
import tempfile
import threading
from shutil import move
import sh
from xdg.BaseDirectory import xdg_data_home, xdg_config_home
from rho.translation import _


RHO_PATH = 'rho'
CONFIG_DIR = os.path.join(xdg_config_home, RHO_PATH)
DATA_DIR = os.path.join(xdg_data_home, RHO_PATH)
CREDENTIALS_PATH = os.path.join(CONFIG_DIR, 'credentials')
PROFILES_PATH = os.path.join(CONFIG_DIR, 'profiles')
PING_INVENTORY_PATH = os.path.join(CONFIG_DIR, 'ping-inventory.yml')
RHO_LOG = os.path.join(DATA_DIR, 'rho_log')
PING_LOG_PATH = os.path.join(DATA_DIR, 'ping_log')
ANSIBLE_LOG_PATH = os.path.join(DATA_DIR, 'ansible_log')
SCAN_LOG_PATH = os.path.join(DATA_DIR, 'scan_log')

PROFILE_HOSTS_SUFIX = '_hosts.yml'
PROFILE_HOST_AUTH_MAPPING_SUFFIX = '_host_auth_mapping'

PLAYBOOK_DEV_PATH = 'rho_playbook.yml'
PLAYBOOK_RPM_PATH = '/usr/share/ansible/rho/rho_playbook.yml'

PASSWORD_MASKING = '********'


# 'log' is a convenience for getting the appropriate logger from the
# logging module. Use it like this:
#
#   from rho.utilities import log
#   ...
#   log.error('Too many Tribbles!')

# pylint: disable=invalid-name
log = logging.getLogger('rho')


def setup_logging(verbosity):
    """Set up Python logging for Rho.

    Must be run after ensure_data_dir_exists().

    :param verbosity: verbosity level, as measured in -v's on the command line.
        Can be None for default.
    """

    if verbosity is None:
        log_level = logging.WARNING
    elif verbosity == 1:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    # Using basicConfig here means that all log messages, even
    # those not coming from rho, will go to the log file
    logging.basicConfig(filename=RHO_LOG)
    # but we only adjust the log level for the 'rho' logger.
    log.setLevel(log_level)
    # the StreamHandler sends warnings and above to stdout, but
    # only for messages going to the 'rho' logger, i.e. Rho
    # output.
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    log.addHandler(stderr_handler)


def threaded_tailing(path, ansible_verbosity=0):
    """Follow and provide output using a thread

    :param path: path to file to follow
    :param ansible_verbosity: the verbosity level
    """
    thread = threading.Thread(
        target=tail_and_follow, args=(path, ansible_verbosity))
    thread.daemon = True
    thread.start()


def tail_and_follow(path, ansible_verbosity):
    """Follow and provide output

    :param path: tuple containing thepath to file to follow
    :param ansible_verbosity: the verbosity level
    """
    if len(path) > 0:  # pylint: disable=len-as-condition
        truncate = 1
        if ansible_verbosity:
            truncate = ansible_verbosity

        print_line = truncate
        plabook_started = False
        truncated = False

        # pylint: disable=no-member
        for line in sh.tail('-f', '-n', '+0', path, _iter=True):
            line = line.strip('\n')
            if line.startswith('TASK') or line.startswith('PLAY'):
                print(line)
                print_line = truncate
                plabook_started = True
                truncated = False
            elif print_line > 0:
                line_len = len(line)
                char_truncate = truncate * 100
                if line_len > char_truncate:
                    print(line[0:char_truncate] + '...')
                else:
                    print(line)
                print_line = print_line - 1
            elif print_line == 0 and not truncated and plabook_started:
                print(_('-- output truncated --'))
                truncated = True


def ensure_config_dir_exists():
    """Ensure the Rho configuration directory exists."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)


def ensure_data_dir_exists():
    """Ensure the Rho data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


# pylint: disable=unused-argument
def multi_arg(option, opt_str, value, parser):
    """Call back function for arg-parse for when arguments are multiple

    :param option: The option
    :param opt_str: The option string
    :param value: The value
    :param parser: The parser for handling the option
    """
    args = []
    for arg in parser.rargs:
        if arg[0] != "-":
            args.append(arg)
        else:
            del parser.rargs[:len(args)]
            break
    if getattr(parser.values, option.dest):
        args.extend(getattr(parser.values, option.dest))
    setattr(parser.values, option.dest, args)


# Read in a file and make it a list
def _read_in_file(filename):
    result = None
    hosts = None
    try:
        hosts = open(os.path.expanduser(os.path.expandvars(filename)), "r")
        result = hosts.read().splitlines()
        hosts.close()
    except EnvironmentError as err:
        sys.stderr.write('Error reading from %s: %s\n' % (filename, err))
        hosts.close()
    return result


# Makes sure the hosts passed in are in a format Ansible
# understands.
# pylint: disable=too-many-locals, too-many-branches, too-many-statements
def read_ranges(ranges_or_path):
    """Process a range list from the user.

    This function reads a hosts file if necessary, validates that all
    IP ranges are in Ansible format, and rewrites CIDR address ranges
    to Ansible format if necessary.

    :param ranges_or_path: either a list of IP address ranges or a one-element
        list where the one element is the path of a file with ranges.
    :returns: list of IP address ranges in Ansible format

    """

    invalid_path = check_path_validity([ranges_or_path[0]])
    if ranges_or_path and os.path.isfile(ranges_or_path[0]):
        hosts = _read_in_file(ranges_or_path[0])
    elif invalid_path == [] and len(ranges_or_path) == 1:
        log.error(_("Couldn't interpret %s as host file because "
                    "no such file exists."), ranges_or_path[0])
        sys.exit(1)
    else:
        hosts = ranges_or_path

    # Regex for octet, CIDR bit range, and check
    # to see if it is like an IP/CIDR
    octet_regex = r'(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])'
    bit_range = r'(3[0-2]|[1-2][0-9]|[0-9])'
    relaxed_ip_pattern = r'[0-9]*\.[0-9]*\.[0-9\[\]:]*\.[0-9\[\]:]*'
    relaxed_cidr_pattern = r'[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*\/[0-9]*'
    relaxed_invalid_ip_range = r'[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*-' \
                               r'[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*'

    # type IP:          192.168.0.1
    # type CIDR:        192.168.0.0/16
    # type RANGE 1:     192.168.0.[1:15]
    # type RANGE 2:     192.168.[2:18].1
    # type RANGE 3:     192.168.[2:18].[4:46]
    ip_regex_list = [
        r'^{0}\.{0}\.{0}\.{0}$'.format(octet_regex),
        r'^{0}\.{0}\.{0}\.{0}\/{1}$'.format(octet_regex, bit_range),
        r'^{0}\.{0}\.{0}\.\[{0}:{0}\]$'.format(octet_regex),
        r'^{0}\.{0}\.\[{0}:{0}\]\.{0}$'.format(octet_regex),
        r'^{0}\.{0}\.\[{0}:{0}\]\.\[{0}:{0}\]$'.format(octet_regex)
    ]

    # type HOST:                abcd
    # type HOST NUMERIC RANGE:  abcd[2:4].foo.com
    # type HOST ALPHA RANGE:    abcd[a:f].foo.com
    host_regex_list = [
        r'[a-zA-Z0-9-\.]+',
        r'[a-zA-Z0-9-\.]*\[[0-9]+:[0-9]+\]*[a-zA-Z0-9-\.]*',
        r'[a-zA-Z0-9-\.]*\[[a-zA-Z]{1}:[a-zA-Z]{1}\][a-zA-Z0-9-\.]*']

    normalized_hosts = []
    host_errors = []

    for host in hosts:
        result = None
        host_range = host

        ip_match = re.match(relaxed_ip_pattern, host_range)
        cidr_match = re.match(relaxed_cidr_pattern, host_range)
        invalid_ip_range_match = re.match(relaxed_invalid_ip_range,
                                          host_range)
        is_likely_ip = ip_match and ip_match.end() == len(host_range)
        is_likely_cidr = cidr_match and cidr_match.end() == len(host_range)
        is_likely_invalid_ip_range = (invalid_ip_range_match and
                                      invalid_ip_range_match.end() ==
                                      len(host_range))

        if is_likely_invalid_ip_range:
            err_message = '{} is not a valid IP range format'
            result = ValueError(err_message .format(host_range))

        elif is_likely_ip or is_likely_cidr:
            # This is formatted like an IP or CIDR
            # (e.g. #.#.#.# or #.#.#.#/#)
            for reg in ip_regex_list:
                match = re.match(reg, host_range)
                if match and match.end() == len(host_range):
                    result = host
                    break

            if result is None or is_likely_cidr:
                # Attempt to convert CIDR to ansible range
                if is_likely_cidr:
                    try:
                        normalized_cidr = cidr_to_ansible(host_range)
                        result = normalized_cidr
                    except ValueError as validate_error:
                        result = validate_error
                else:
                    err_message = '{} is not a valid IP or CIDR pattern'
                    result = ValueError(err_message.format(host_range))
        else:
            # Possibly a host addr
            for reg in host_regex_list:
                match = re.match(reg, host_range)
                if match and match.end() == len(host_range):
                    result = host
                    break
            if result is None:
                result = ValueError(
                    '{} is invalid host'.format(host_range))

        if isinstance(result, ValueError):
            host_errors.append(result)
        elif result is not None:
            normalized_hosts.append(result)
        else:
            # This is an unexpected case. Allow/log for analysis
            normalized_hosts.append(host)
            logging.warning('%s did not match a pattern or produce error',
                            host_range)
    if len(host_errors) is 0:
        return normalized_hosts
    else:
        for host_error in host_errors:
            print(host_error)
        sys.exit(1)

    return normalized_hosts


class NotCIDRException(Exception):
    """Exception for when a string does not look like a CIDR range."""

    pass


# pylint: disable=too-many-locals
def cidr_to_ansible(ip_range):
    """Convert an IP address range from CIDR to Ansible notation.

    :param ip_range: the IP range, as a string
    :returns: the IP range, as an Ansible-formatted string
    :raises NotCIDRException: if ip_range doesn't look similar to CIDR
        notation. If it does look like CIDR but isn't quite right, print out
        error messages and exit.
    """

    # In the case of an input error, we want to distinguish between
    # strings that are "CIDR-like", so the user probably intended to
    # use CIDR and we should give them a CIDR error message, and not
    # at all CIDR-like, in which case we tell the caller to parse it a
    # different way.
    cidr_like = r'[0-9.]*/[0-9]*'
    err_prefix = 'A error occurred parsing an input host value. '
    if not re.match(cidr_like, ip_range):
        raise NotCIDRException

    try:
        base_address, prefix_bits = ip_range.split('/')
    except ValueError:
        err_msg = err_prefix + 'IP range %s has invalid format.'
        log.error(err_msg, ip_range)
        sys.exit(1)

    prefix_bits = int(prefix_bits)

    if prefix_bits < 0 or prefix_bits > 32:
        err_msg = err_prefix + 'Bit mask length %s of IP range %s is not in ' \
            'the valid range [0,32].'
        log.error(err_msg, prefix_bits, ip_range)
        sys.exit(1)

    octet_strings = base_address.split('.')
    if len(octet_strings) != 4:
        err_msg = err_prefix + 'IP address %s (part of IP range %s) ' \
            'does not have exactly 4 octets'
        log.error(err_msg, base_address, ip_range)
        sys.exit(1)

    octets = [None] * 4
    for i in range(4):
        if not octet_strings[i]:
            err_msg = err_prefix + 'Empty octet in IP range %s'
            log.error(err_msg, ip_range)
            sys.exit(1)

        val = int(octet_strings[i])
        if val < 0 or val > 255:
            err_msg = err_prefix + 'IP octet %s (part of IP range %s) ' \
                'is not in the valid range [0,255]'
            log.error(err_msg, val, ip_range)
            sys.exit(1)
        octets[i] = val

    ansible_out = [None] * 4
    for i in range(4):
        # "prefix_bits" is the number of high-order bits we want to
        # keep for the whole CIDR range. "mask" is the number of
        # low-order bits we want to mask off. Here prefix_bits is for
        # the whole IP address, but mask_bits is just for this octet.

        if prefix_bits <= i * 8:
            ansible_out[i] = '[0:255]'
        elif prefix_bits >= (i + 1) * 8:
            ansible_out[i] = str(octets[i])
        else:
            # The number of bits of this octet that we want to
            # preserve
            this_octet_bits = prefix_bits - 8 * i
            assert 0 < this_octet_bits < 8
            # mask is this_octet_bits 1's followed by (8 -
            # this_octet_bits) 0's.
            mask = -1 << (8 - this_octet_bits)

            lower_bound = octets[i] & mask
            upper_bound = lower_bound + ~mask
            ansible_out[i] = '[{0}:{1}]'.format(
                lower_bound, upper_bound)

    return '.'.join(ansible_out)


def validate_port(arg):
    """Check that arg is a valid port.

    :param arg: either a string or an integer.
    :returns: The arg, as an integer.
    :raises: ValueError, if arg is not a valid port.
    """

    if isinstance(arg, str):
        try:
            arg = int(arg)
        except ValueError:
            raise ValueError('Port value %s'
                             ' should be a positive integer'
                             ' in the valid range (0-65535)' % arg)
    elif not isinstance(arg, int):
        raise ValueError('Port value %s should be a positive integer'
                         ' in the valid range (0-65535)' % arg)

    # We need to support both system and user ports (see
    # https://en.wikipedia.org/wiki/Registered_port) because we don't
    # know how the user will have configured their system.
    if arg < 0 or arg > 65535:
        raise ValueError('Port value %s should be a positive integer'
                         ' in the valid range (0-65535)' % arg)

    return arg


def str_to_ascii(in_string):
    """ Coverts unicode string to ascii string

    :param in_string: input string to convert to ascii
    :returns: ASCII encoded string
    """
    if sys.version_info[0] == 2:
        return in_string.decode('utf-8').encode('ascii')

    return in_string


def iteritems(dictionary):
    """Iterate over a dictionary's (key, value) pairs using Python 2 or 3.

    :param dictionary: the dictionary to iterate over.
    """

    if sys.version_info[0] == 2:
        return dictionary.iteritems()

    return dictionary.items()


if sys.version_info[0] == 2:
    def is_stringlike(obj):
        """Check if an object is a string.

        This function is for Python 2 and 3 compatibility.
        """

        # pylint for python 3 complains that unicode is undefined.
        # pylint: disable=undefined-variable
        return isinstance(obj, (str, unicode))
else:
    def is_stringlike(obj):
        """Check if an object is a string.

        This function is for Python 2 and 3 compatibility.
        """

        return isinstance(obj, str)


def write_csv_data(keys, data, path):
    """ Write csv data with input fieldnames a dictionary of data and the file
    path to write to.

    :param keys: The field names and keys of the dictionary
    :param data: The dictionary of data to convert to csv
    :param path: The file path to write to
    """
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as data_temp:
        # Construct the CSV writer
        writer = csv.DictWriter(
            data_temp, fieldnames=sorted(keys), delimiter=',')

        # Write a CSV header if necessary;
        # handle Python 2.6 not having writeheader method
        if sys.version_info[0] == 2 and sys.version_info[1] <= 6:
            headers = {}
            for fields in writer.fieldnames:
                headers[fields] = fields
            writer.writerow(headers)
        else:
            writer.writeheader()

        # Write the data
        for row in data:
            writer.writerow(row)
    data_temp.close()
    move(data_temp.name, path)


def get_config_path(filename):
    """Provides the path for a configuration filename

    :param filename: The filename to return the config path for
    :returns: path to for filename in XDG_CONFIG_HOME associated with rho
    """
    return os.path.join(xdg_config_home, RHO_PATH, filename)


def check_path_validity(path_list):
    """Given a list of paths it verifies that all paths are valid absolute
    path inputs for a scoped scan. If not it return a list of invalid paths.

    :param path_list: list of paths to validate
    :return: empty list or list of invalid paths
    """
    invalid_paths = []
    for a_path in path_list:
        if not os.path.isabs(a_path):
            invalid_paths.append(a_path)
    return invalid_paths
