#
# Copyright (c) 2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

# pylint: disable=R0903

"""Module responsible for displaying results of rho report"""

import csv
import os
import json
import sys
import xml
# pylint: disable=import-error
from ansible.module_utils.basic import AnsibleModule

# for parsing systemid
if sys.version_info > (3,):
    import xmlrpc.client as xmlrpclib  # pylint: disable=import-error
    long = int  # pylint: disable=invalid-name,redefined-builtin
else:
    import xmlrpclib  # pylint: disable=import-error

EAP_CLASSIFICATIONS = {
    'JBoss_4_0_0': 'JBossAS-4',
    'JBoss_4_0_1_SP1': 'JBossAS-4',
    'JBoss_4_0_2': 'JBossAS-4',
    'JBoss_4_0_3_SP1': 'JBossAS-4',
    'JBoss_4_0_4_GA': 'JBossAS-4',
    'Branch_4_0': 'JBossAS-4',
    'JBoss_4_2_0_GA': 'JBossAS-4',
    'JBoss_4_2_1_GA': 'JBossAS-4',
    'JBoss_4_2_2_GA': 'JBossAS-4',
    'JBoss_4_2_3_GA': 'JBossAS-4',
    'JBoss_5_0_0_GA': 'JBossAS-5',
    'JBoss_5_0_1_GA': 'JBossAS-5',
    'JBoss_5_1_0_GA': 'JBossAS-5',
    'JBoss_6.0.0.Final': 'JBossAS-6',
    'JBoss_6.1.0.Final': 'JBossAS-6',
    '1.0.1.GA': 'JBossAS-7',
    '1.0.2.GA': 'JBossAS-7',
    '1.1.1.GA': 'JBossAS-7',
    '1.2.0.CR1': 'JBossAS-7',
    '1.2.0.Final': 'WildFly-8',
    '1.2.2.Final': 'WildFly-8',
    '1.2.4.Final': 'WildFly-8',
    '1.3.0.Beta3': 'WildFly-8',
    '1.3.0.Final': 'WildFly-8',
    '1.3.3.Final': 'WildFly-8',
    '1.3.4.Final': 'WildFly-9',
    '1.4.2.Final': 'WildFly-9',
    '1.4.3.Final': 'WildFly-9',
    '1.4.4.Final': 'WildFly-10',
    '1.5.0.Final': 'WildFly-10',
    '1.5.1.Final': 'WildFly-10',
    '1.5.2.Final': 'WildFly-10',
    'JBPAPP_4_2_0_GA': 'EAP-4.2',
    'JBPAPP_4_2_0_GA_C': 'EAP-4.2',
    'JBPAPP_4_3_0_GA': 'EAP-4.3',
    'JBPAPP_4_3_0_GA_C': 'EAP-4.3',
    'JBPAPP_5_0_0_GA': 'EAP-5.0.0',
    'JBPAPP_5_0_1': 'EAP-5.0.1',
    'JBPAPP_5_1_0': 'EAP-5.1.0',
    'JBPAPP_5_1_1': 'EAP-5.1.1',
    'JBPAPP_5_1_2': 'EAP-5.1.2',
    'JBPAPP_5_2_0': 'EAP-5.2.0',
    '1.1.2.GA-redhat-1': 'EAP-6.0.0',
    '1.1.3.GA-redhat-1': 'EAP-6.0.1',
    '1.2.0.Final-redhat-1': 'EAP-6.1.0',
    '1.2.2.Final-redhat-1': 'EAP-6.1.1',
    '1.3.0.Final-redhat-2': 'EAP-6.2',
    '1.3.3.Final-redhat-1': 'EAP-6.3',
    '1.3.4.Final-redhat-1': 'EAP-6.3',
    '1.3.5.Final-redhat-1': 'EAP-6.3',
    '1.3.6.Final-redhat-1': 'EAP-6.4',
    '1.3.7.Final-redhat-1': 'EAP-6.4',
    '1.4.4.Final-redhat-1': 'EAP-7.0',
    '1.5.1.Final-redhat-1': 'EAP-7.0',
    '1.5.4.Final-redhat-1': 'EAP-7.0'
}

BRMS_CLASSIFICATIONS = {
    '6.4.0.Final-redhat-3': 'BRMS 6.3.0',
    '6.3.0.Final-redhat-5': 'BRMS 6.2.0',
    '6.2.0.Final-redhat-4': 'BRMS 6.1.0',
    '6.0.3-redhat-6': 'BRMS 6.0.3',
    '6.0.3-redhat-4': 'BRMS 6.0.2',
    '6.0.2-redhat-6': 'BRMS 6.0.1',
    '6.0.2-redhat-2': 'BRMS 6.0.0',
    '5.3.1.BRMS': 'BRMS 5.3.1',
    '5.3.0.BRMS': 'BRMS 5.3.0',
    '5.2.0.BRMS': 'BRMS 5.2.0',
    '5.1.0.BRMS': 'BRMS 5.1.0',
    '5.0.2.BRMS': 'BRMS 5.0.2',
    '5.0.1.BRMS': 'BRMS 5.0.1',
    'drools-core-5.0.0': 'BRMS 5.0.0',
    '6.5.0.Final': 'Drools 6.5.0'
}

FUSE_CLASSIFICATIONS = {
    'redhat-630187': 'Fuse-6.3.0',
    'redhat-621084': 'Fuse-6.2.1',
    'redhat-620133': 'Fuse-6.2.0',
    'redhat-611412': 'Fuse-6.1.1',
    'redhat-610379': 'Fuse-6.1.0',
    'redhat-60024': 'Fuse-6.0.0',
}


def iteritems(dictionary):
    """Iterate over a dictionary's (key, value) pairs using Python 2 or 3.

    :param dictionary: the dictionary to iterate over.
    """

    if sys.version_info[0] == 2:
        return dictionary.iteritems()

    return dictionary.items()


def safe_next(iterator):
    """Get the next item from an iterator, in Python 2 or 3.

    :param iterator: the iterator.
    """

    if sys.version_info[0] == 2:
        return iterator.next()

    return next(iterator)


def raw_output_present(fact_names, host_vars, this_fact, this_var, command):
    """Basic sanity checks for processing an Ansible raw command.

    :param fact_names: the facts to be collected
    :param host_vars: all variables collected for a host
    :param this_fact: the name of the fact we are processing
    :param this_var: the name that Ansible has for our output
    :param command: the command that was run

    :returns: a tuple of
        (None or error dict, None or raw command output).
        The error dict is suitable for inclusion in the rho output
        dictionary. There will not be both errors and raw command
        output. If raw command output is returned, it will have
        fields 'rc' and 'stdout_lines' or 'results'.

    Usage:
        err, output = raw_output_present(...)
        if err is not None:
            return err

        ... process output ...
    """

    if this_fact not in fact_names:
        return {}, None

    if this_var not in host_vars:
        return {this_fact: 'Error: "{0}" not run'.format(command)}, None

    raw_output = host_vars[this_var]

    if (('rc' not in raw_output or
         'stdout_lines' not in raw_output) and 'results' not in raw_output):
        return (
            {this_fact:
             'Error: could not get output from "{0}"'.format(command)},
            None)

    return None, raw_output


JBOSS_EAP_INSTALLED_VERSIONS = 'jboss.eap.installed-versions'
JBOSS_EAP_DEPLOY_DATES = 'jboss.eap.deploy-dates'
JBOSS_EAP_RUNNING_PATHS = 'jboss.eap.running-paths'

FIND_WARNING = 'find: WARNING: Hard link count is wrong for /proc: this may' \
    ' be a bug in your filesystem driver.'
GENERIC_ERROR = 'error'


# JBoss versions are processed separately from other *-ver data
# because they merge data from two input facts and include deploy
# dates as well as version strings.
def process_jboss_versions(fact_names, host_vars):
    """Get JBoss version information from the host_vars.

    :param fact_names: the set of fact names the user requested.
    :param host_vars: the host vars from Ansible.
    :returns: a dict of key-value pairs to output.
    """

    lines = []
    val = {}

    # host_vars is not used after this function (data that we return
    # is copied to host_vals instead), so by not adding
    # jboss.eap.jar_ver and jboss.eap.run_jar_ver to val, we are
    # implicitly removing them from the output.
    err, output = raw_output_present(fact_names, host_vars,
                                     'jboss.eap.jar-ver',
                                     'jboss.eap.jar-ver',
                                     'scan for jboss-modules.jar')
    if err is not None:
        return err
    lines.extend(output['stdout_lines'])

    err, output = raw_output_present(fact_names, host_vars,
                                     'jboss.eap.run-jar-ver',
                                     'jboss.eap.run-jar-ver',
                                     'scan for running JBoss EAP')
    if err is not None:
        return err
    lines.extend(output['stdout_lines'])

    jboss_releases = []
    deploy_dates = []
    for line in lines:
        if line:
            line_format = line.split('**')
            version = line_format[0]
            deploy_date = line_format[-1]
            deploy_dates.append(deploy_date)
            if version in EAP_CLASSIFICATIONS:
                jboss_releases.append(EAP_CLASSIFICATIONS[version])
            elif version.strip():
                jboss_releases.append('Unknown-Release: ' + version)

    def empty_output_message(val, name):
        """Give the right error message for missing data.

        For data that depends on having Java.

        :param val: a value. Considered missing if falsey.
        :param name: the thing we were searching for.
        :returns: the val if true, otherwise a useful error message.
        """

        if val:
            return val
        if not host_vars['have_java']:
            return 'N/A (java not found)'
        return '({0} not found)'.format(name)

    if JBOSS_EAP_INSTALLED_VERSIONS in fact_names:
        val[JBOSS_EAP_INSTALLED_VERSIONS] = (
            empty_output_message('; '.join(jboss_releases), 'jboss'))
    if JBOSS_EAP_DEPLOY_DATES in fact_names:
        val[JBOSS_EAP_DEPLOY_DATES] = (
            empty_output_message('; '.join(deploy_dates), 'jboss'))
    if JBOSS_EAP_RUNNING_PATHS in fact_names:
        err, output = raw_output_present(fact_names, host_vars,
                                         JBOSS_EAP_RUNNING_PATHS,
                                         JBOSS_EAP_RUNNING_PATHS,
                                         'running EAP scan')
        if err is not None:
            val.update(err)
        elif FIND_WARNING in output['stdout']:
            val[JBOSS_EAP_RUNNING_PATHS] = GENERIC_ERROR
        else:
            val[JBOSS_EAP_RUNNING_PATHS] = empty_output_message(
                output['stdout'], 'running EAP scan')

    return val


def classify_releases(lines, classifications):
    """Classify release strings using a dictionary."""

    releases = []
    for line in lines:
        if line:
            if line in classifications:
                releases.append(classifications[line])
            else:
                releases.append('Unknown-Release: ' + line)

    return '; '.join(releases)


def process_addon_versions(fact_names, host_vars):
    """Classify release strings for JBoss BRMS and FUSE.

    :param fact_names: the set of fact names that the user requested.
    :param host_vars: the host vars from Ansible.
    :returns: a dict of key-value pairs to output.
    """

    result = {}

    def classify(key, fact_names, classifications):
        """Classify a particular key."""

        if key in fact_names:
            err, output = raw_output_present(fact_names, host_vars,
                                             key, key, key)
            if err is not None:
                result.update(err)
                return

            classes = classify_releases(output['stdout_lines'],
                                        classifications)
            if classes:
                result[key] = classes
            else:
                result[key] = '({0} not found)'.format(key)

    classify('jboss.brms.kie-api-ver', fact_names, BRMS_CLASSIFICATIONS)
    classify('jboss.brms.drools-core-ver', fact_names, BRMS_CLASSIFICATIONS)
    classify('jboss.brms.kie-war-ver', fact_names, BRMS_CLASSIFICATIONS)

    classify('jboss.fuse.activemq-ver', fact_names, FUSE_CLASSIFICATIONS)
    classify('jboss.fuse.camel-ver', fact_names, FUSE_CLASSIFICATIONS)
    classify('jboss.fuse.cxf-ver', fact_names, FUSE_CLASSIFICATIONS)

    return result


JBOSS_EAP_JBOSS_USER = 'jboss.eap.jboss-user'


def process_id_u_jboss(fact_names, host_vars):
    """Process the output from 'id -u jboss', as run by Ansible

    :returns: a dict of key-value pairs to add to the output.
    """

    # We use the 'id' command to check for jboss because it's been in
    # GNU coreutils since 1992, so it should be present on every
    # system we encounter.

    err, output = raw_output_present(fact_names, host_vars,
                                     'jboss.eap.jboss-user',
                                     'jboss_eap_id_jboss',
                                     'id -u jboss')
    if err is not None:
        return err

    if output['rc'] == 0:
        return {JBOSS_EAP_JBOSS_USER: "User 'jboss' present"}

    # Don't output a definitive "not found" unless we see an error
    # string that we recognize. We don't want to assume that any
    # nonzero error code means "not found", because then we would give
    # false negatives if the user didn't have permission to read
    # /etc/passwd (or other errors).
    if output['stdout_lines'] == ['id: jboss: no such user']:
        return {JBOSS_EAP_JBOSS_USER: 'No user "jboss" found'}

    return {JBOSS_EAP_JBOSS_USER:
            'Error: unexpected output from "id -u jboss": %s' % output}


JBOSS_EAP_COMMON_FILES = 'jboss.eap.common-files'


def process_jboss_eap_common_files(fact_names, host_vars):
    """Process the output of 'test -e <dir>', for common install paths.

    :returns: a dict of key, value pairs to add to the output.
    """

    err, output = raw_output_present(fact_names, host_vars,
                                     'jboss.eap.common-files',
                                     'jboss_eap_common_files',
                                     'common file and directory tests')

    if err is not None:
        return err

    items = output['results']

    out_list = []
    for item in items:
        directory = item['item']

        if 'rc' in item and item['rc'] == 0:
            out_list.append(directory)

        # If 'rc' is in item but is nonzero, the directory wasn't
        # present. If 'rc' isn't in item, there was an error and the
        # test wasn't run. Unfortunately, we don't have the ability to
        # get logs out of spit_results, so we'll have to hope the
        # scan_log is enough to debug any problems we have. :(

    return {JBOSS_EAP_COMMON_FILES:
            ';'.join(('{0} found'.format(directory)
                      for directory in out_list))}


JBOSS_EAP_PROCESSES = 'jboss.eap.processes'


def process_jboss_eap_processes(fact_names, host_vars):
    """Process the output of 'ps -A -f e | grep eap'

    :returns: a dict of key, value pairs to add to the output.
    """

    # Why use 'ps -A -f e | grep eap'? The -A gets us every process on
    # the system, and -f means ps will print the command-line
    # arguments, which is key because JBoss will be invoked with java
    # as the executable and an argument that says to run the Wildfly
    # jar.

    # The e makes ps print the process's environment. It's in a format
    # that is not machine-readable, because ps uses spaces as the
    # delimiter for both command-line args and the process
    # environment, and we have no way to tell where the arguments end
    # and the environment begins. However, that's fine for grepping. I
    # observed an EAP 7 application server running with MANPATH,
    # JBOSS_MODULEPATH, JBOSS_HOME, WILDFLY_CONSOLE_LOG, WILDFLY_SH,
    # LD_LIBRARY_PATH, EAP7_SCLS_ENABLED, PATH, WILDFLY_MODULEPATH,
    # HOME, and PKG_CONFIG_PATH set to directories that included
    # /opt/rh/eap7, all of which will be caught by our
    # grep. Additionally, variables LAUNCH_JBOSS_IN_BACKGROUND and
    # JBOSS_HOME will be caught because of the variable names
    # themselves. We deliberately don't grep for wildfly or jboss,
    # because that could catch non-JBoss Wildfly installations.

    err, output = raw_output_present(fact_names, host_vars,
                                     JBOSS_EAP_PROCESSES,
                                     JBOSS_EAP_PROCESSES,
                                     'ps -A -f e | grep eap')
    if err is not None:
        return err

    # pgrep exists with status 0 if it finds processes matching its
    # pattern, and status 1 if not.
    if output['rc']:
        return {JBOSS_EAP_PROCESSES: 'No EAP processes found'}

    num_procs = len(output['stdout_lines'])

    # There should always be two processes matching 'eap', one for the
    # grep that's searching for 'eap', and one for the bash that's
    # running the pipeline.
    if num_procs < 2:
        return {
            JBOSS_EAP_PROCESSES:
            "Bad result ({0} processes) from 'ps -A -f e | grep eap'".format(
                num_procs)}

    return {JBOSS_EAP_PROCESSES:
            '{0} EAP processes found'.format(num_procs - 2)}


JBOSS_EAP_PACKAGES = 'jboss.eap.packages'


def process_jboss_eap_packages(fact_names, host_vars):
    """Process the list of JBoss EAP-related RPMs.

    :returns: a dict of key, value pairs to add to the output.
    """

    # We use (eap7)|(jbossas) as the pattern because all of the EAP 6
    # packages had the prefix jbossas- and all of the EAP 7 packages
    # have the prefix eap7-. We set a custom format for rpm output and
    # get a lot of package fields, even though we only use the number
    # of output lines, so we will have full package data in the logs
    # if customers have questions about the number. Hopefully in the
    # future we can surface that data through a UI.

    err, output = raw_output_present(fact_names, host_vars,
                                     JBOSS_EAP_PACKAGES,
                                     JBOSS_EAP_PACKAGES,
                                     "rpm -q -a | grep -E '(eap7)|(jbossas)'")
    if err is not None:
        return err

    # the sort on the end of the pipeline returns 0 whether or not
    # matches were found, so a nonzero return code should never
    # happen.
    if output['rc']:
        return {JBOSS_EAP_PACKAGES: 'Pipeline returned non-zero status'}

    num_packages = len(output['stdout_lines'])

    return {JBOSS_EAP_PACKAGES:
            '{0} JBoss-related packages found'.format(num_packages)}


JBOSS_EAP_LOCATE_JBOSS_MODULES_JAR = 'jboss.eap.locate-jboss-modules-jar'


def process_jboss_eap_locate(fact_names, host_vars):
    """Process the results of 'locate jboss-modules.jar'.

    :returns: a dict of key, value pairs to add to the output.
    """

    err, output = raw_output_present(fact_names, host_vars,
                                     JBOSS_EAP_LOCATE_JBOSS_MODULES_JAR,
                                     'jboss_eap_locate_jboss_modules_jar',
                                     'locate jboss-modules.jar')
    if err is not None:
        return err

    if not output['rc'] and output['stdout_lines']:
        return {JBOSS_EAP_LOCATE_JBOSS_MODULES_JAR:
                ';'.join(output['stdout_lines'])}

    if output['rc'] and not output['stdout_lines']:
        return {JBOSS_EAP_LOCATE_JBOSS_MODULES_JAR:
                'jboss-modules.jar not found'}

    return {JBOSS_EAP_LOCATE_JBOSS_MODULES_JAR:
            "Error code {0} running 'locate jboss-modules.jar': {1}".format(
                output['rc'], output['stdout'])}


JBOSS_EAP_INIT_FILES = 'jboss.eap.init-files'


def process_jboss_eap_init_files(fact_names, host_vars):
    """Look for jboss and EAP in init system output.

    :returns: a dict of key, value pairs to add to the output.
    """

    # The init system changed between RHEL 6 and RHEL 7. 'chkconfig'
    # should work on RHEL 6, and 'systemctl list-unit-files' should
    # work on RHEL 7.
    err, chkconfig = raw_output_present(fact_names, host_vars,
                                        JBOSS_EAP_INIT_FILES,
                                        'jboss_eap_chkconfig',
                                        'chkconfig')
    if err is not None:
        return err

    err, systemctl = raw_output_present(fact_names, host_vars,
                                        JBOSS_EAP_INIT_FILES,
                                        'jboss_eap_systemctl_unit_files',
                                        'systemctl list-unit-files')
    if err is not None:
        return err

    if chkconfig['rc'] and systemctl['rc']:
        return {JBOSS_EAP_INIT_FILES:
                'Error: all init system checks failed.'}

    # On a RHEL 6 system, chkconfig will return a list of available
    # services and systemctl will error. On a RHEL 7 system, systemctl
    # will return a list of system services and chkconfig will return
    # a shorter list of services and a warning message to go look at
    # systemctl. However, users may well choose to run JBoss under the
    # old init system on RHEL 7 due to familiarity or lack of need to
    # change, so we look in all available output.

    def find_services(lines, method):
        """Find system services matching 'jboss' or 'eap'

        :returns: a list of the services, as strings, with the method.
        """

        output = []
        for line in lines:
            if not line:
                continue

            service = line.split()[0]
            if 'jboss' in service or 'eap' in service:
                output.append('{0} ({1})'.format(service, method))

        return output

    found_services = []
    if not chkconfig['rc']:
        found_services.extend(find_services(chkconfig['stdout_lines'],
                                            'chkconfig'))
    if not systemctl['rc']:
        found_services.extend(find_services(systemctl['stdout_lines'],
                                            'systemctl'))

    if found_services:
        return {JBOSS_EAP_INIT_FILES:
                '; '.join(found_services)}

    return {JBOSS_EAP_INIT_FILES:
            "No services found matching 'jboss' or 'eap'."}


def escape_characters(data):
    """ Processes input data values and strips out any newlines or commas
    """
    for key in data:
        if isinstance(data[key], str):
            data[key] = data[key].replace('\r\n', ' ').replace(',', ' ')
    return data


# pylint: disable=no-self-use
def determine_pkg_facts(rh_packages):
    """Gets the last installed and last build packages from the list

    :param rh_packages: the filtered list of red hat packages
    :returns: tuple of last installed and last built
    """
    last_installed = None
    last_built = None
    max_install_time = float("-inf")
    max_build_time = float("-inf")
    is_red_hat = 'Y' if rh_packages else 'N'

    for pkg in rh_packages:
        if pkg.install_time > max_install_time:
            max_install_time = pkg.install_time
            last_installed = pkg
            if pkg.build_time > max_build_time:
                max_build_time = pkg.build_time
                last_built = pkg

    last_installed_val = (last_installed.details_install()
                          if last_installed else 'none')
    last_built_val = (last_built.details_built() if last_built else 'none')
    return is_red_hat, last_installed_val, last_built_val


# pylint: disable=too-many-locals, too-many-branches, too-many-statements
def handle_redhat_packages(facts, data):
    """ Process the output of redhat-packages.results
    and supply the appropriate output information
    """
    if 'redhat-packages.results' in data:
        rhpkg_prefix = 'redhat-packages.'
        gpg_prefix = rhpkg_prefix + 'gpg.'
        is_rhpkg_str = rhpkg_prefix + 'is_redhat'
        num_rh_str = rhpkg_prefix + 'num_rh_packages'
        installed_pkg_str = rhpkg_prefix + 'num_installed_packages'
        last_installed_str = rhpkg_prefix + 'last_installed'
        last_built_str = rhpkg_prefix + 'last_built'
        gpg_is_rhpkg_str = gpg_prefix + 'is_redhat'
        gpg_num_rh_str = gpg_prefix + 'num_rh_packages'
        gpg_installed_pkg_str = gpg_prefix + 'num_installed_packages'
        gpg_last_installed_str = gpg_prefix + 'last_installed'
        gpg_last_built_str = gpg_prefix + 'last_built'
        is_rhpkg_in_facts = is_rhpkg_str in facts
        num_rh_in_facts = num_rh_str in facts
        installed_pkg_in_facts = installed_pkg_str in facts
        last_installed_in_facts = last_installed_str in facts
        last_built_in_facts = last_built_str in facts
        gpg_is_rhpkg_in_facts = gpg_is_rhpkg_str in facts
        gpg_num_rh_in_facts = gpg_num_rh_str in facts
        gpg_installed_pkg_in_facts = gpg_installed_pkg_str in facts
        gpg_last_installed_in_facts = gpg_last_installed_str in facts
        gpg_last_built_in_facts = gpg_last_built_str in facts
        installed_packages = None
        try:
            installed_packages = [PkgInfo(line, "|")
                                  for line in data['redhat-packages.results']]
        except PkgInfoParseException:
            # facts are already initialized as empty strings
            # just remove the results field
            del data['redhat-packages.results']
            return data

        rh_packages = list(filter(PkgInfo.is_red_hat_pkg,
                                  installed_packages))

        rh_gpg_packages = list(filter(PkgInfo.is_gpg_red_hat_pkg,
                                      installed_packages))

        if installed_pkg_in_facts:
            data[installed_pkg_str] = (len(installed_packages))
        if num_rh_in_facts:
            data[num_rh_str] = len(rh_packages)
        if gpg_installed_pkg_in_facts:
            data[gpg_installed_pkg_str] = (len(installed_packages))
        if gpg_num_rh_in_facts:
            data[gpg_num_rh_str] = len(rh_gpg_packages)

        if rh_packages:
            is_red_hat, last_installed, last_built = \
                determine_pkg_facts(rh_packages)
            if is_rhpkg_in_facts:
                data[is_rhpkg_str] = is_red_hat
            if last_installed_in_facts:
                data[last_installed_str] = last_installed
            if last_built_in_facts:
                data[last_built_str] = last_built

        if rh_gpg_packages:
            is_red_hat, last_installed, last_built = \
                determine_pkg_facts(rh_gpg_packages)
            if gpg_is_rhpkg_in_facts:
                data[gpg_is_rhpkg_str] = is_red_hat
            if gpg_last_installed_in_facts:
                data[gpg_last_installed_str] = last_installed
            if gpg_last_built_in_facts:
                data[gpg_last_built_str] = last_built

        del data['redhat-packages.results']
    return data


# pylint: disable=too-many-instance-attributes
class PkgInfo(object):
    """This is an inner class for RedhatPackagesRhoCmd
    class and provides functionality to parse the
    results of running the (only) command string
    named 'get_package_info'. This is purely to
    make the parsing cleaner and understandable.
    """
    RED_HAT_KEYS = ('199e2f91fd431d51', '5326810137017186',
                    '45689c882fa658e0', '219180cddb42a60e',
                    '7514f77d8366b0d9', '45689c882fa658e0')

    def __init__(self, row, separator):
        cols = row.split(separator)
        if len(cols) < 14:
            raise PkgInfoParseException()
        else:
            self.name = cols[0]
            self.version = cols[1]
            self.release = cols[2]
            self.install_time = long(cols[3])
            self.vendor = cols[4]
            self.build_time = long(cols[5])
            self.build_host = cols[6]
            self.source_rpm = cols[7]
            self.license = cols[8]
            self.packager = cols[9]
            self.install_date = cols[10]
            self.build_date = cols[11]
            self.is_red_hat = False
            if ('redhat.com' in self.build_host and
                    'fedora' not in self.build_host and
                    'rhndev' not in self.build_host):
                self.is_red_hat = True
            gpgkeys = (cols[12], cols[13], cols[14], cols[15])
            self.is_red_hat_gpg = False
            for known_key in self.RED_HAT_KEYS:
                for rpm_gpg_key in gpgkeys:
                    if known_key in rpm_gpg_key:
                        self.is_red_hat_gpg = True
                        break
                if self.is_red_hat_gpg:
                    break

            # Helper methods to help with recording data in
            # requested fields.

    def is_red_hat_pkg(self):
        """Determines if package is a Red Hat package.
        :returns: True if Red Hat, False otherwise
        """
        return self.is_red_hat

    def is_gpg_red_hat_pkg(self):
        """Determines if package is a Red Hat package with known GPG key.
        :returns: True if Red Hat, False otherwise
        """
        return self.is_red_hat and self.is_red_hat_gpg

    def details_built(self):
        """Provides information on when the package was built
        :returns: String including details and build date
        """
        return "%s Built: %s" % (self.details(), self.build_date)

    def details_install(self):
        """Provides information on when the package was installed.
        :returns: String including installation date
        """
        return "%s Installed: %s" % (self.details(), self.install_date)

    def details(self):
        """Provides package details including name, version and release.
        :returns: String including name, version and release
        """
        return "%s-%s-%s" % (self.name, self.version, self.release)


class PkgInfoParseException(BaseException):
    """Defining an exception for failing to parse package information
    """
    pass


class Results(object):
    """The class Results contains the functionality to parse
    data passed in from the playbook and to output it in the
    csv format in the file path specified.
    """

    def __init__(self, module):
        self.module = module
        self.name = module.params['name']
        self.file_path = module.params['file_path']
        self.vals = module.params['vals']
        self.all_vars = module.params['all_vars']
        self.fact_names = module.params['fact_names']

    def handle_systemid(self, data):
        """Process the output of systemid.contents
        and supply the appropriate output information
        """
        if 'systemid.contents' in data:
            blob = data['systemid.contents']
            id_in_facts = 'SysId_systemid.system_id' in self.fact_names
            username_in_facts = 'SysId_systemid.username' in self.fact_names
            try:
                systemid = xmlrpclib.loads(blob)[0][0]
                if id_in_facts and 'system_id'in systemid:
                    data['systemid.system_id'] = systemid['system_id']
                if username_in_facts and 'usnername' in systemid:
                    data['systemid.username'] = systemid['usnername']
            except xml.parsers.expat.ExpatError:
                if id_in_facts:
                    data['systemid.system_id'] = 'error'
                if username_in_facts:
                    data['systemid.username'] = 'error'

            del data['systemid.contents']
        return data

    def write_to_csv(self):
        """Output report data to file in csv format"""
        # Make sure the controller expanded the default option.
        assert self.fact_names != ['default']

        keys = set(self.fact_names)

        # Special processing for JBoss facts.
        for _, host_vars in iteritems(self.all_vars):
            uuid = host_vars['connection']['connection.uuid']
            host_vals = safe_next((vals
                                   for vals in self.vals
                                   if vals['connection.uuid'] == uuid))

            host_vals.update(process_jboss_versions(keys, host_vars))
            host_vals.update(process_addon_versions(keys, host_vars))
            host_vals.update(process_id_u_jboss(keys, host_vars))
            host_vals.update(process_jboss_eap_common_files(keys, host_vars))
            host_vals.update(process_jboss_eap_processes(keys, host_vars))
            host_vals.update(process_jboss_eap_packages(keys, host_vars))
            host_vals.update(process_jboss_eap_locate(keys, host_vars))
            host_vals.update(process_jboss_eap_init_files(keys, host_vars))

        # Process System ID.
        for data in self.vals:
            data = self.handle_systemid(data)
            data = handle_redhat_packages(self.fact_names, data)
            data = escape_characters(data)

        normalized_path = os.path.normpath(self.file_path)
        with open(normalized_path, 'w') as write_file:
            # Construct the CSV writer
            writer = csv.DictWriter(
                write_file, sorted(keys), delimiter=',')

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
            for data in self.vals:
                writer.writerow(data)


def main():
    """Function to trigger collection of results and write
    them to csv file
    """

    fields = {
        "name": {"required": True, "type": "str"},
        "file_path": {"required": True, "type": "str"},
        "vals": {"required": True, "type": "list"},
        "all_vars": {"required": True, "type": "dict"},
        "fact_names": {"required": True, "type": "list"}
    }

    module = AnsibleModule(argument_spec=fields)

    results = Results(module=module)
    results.write_to_csv()
    vals = json.dumps(results.vals)
    module.exit_json(changed=False, meta=vals)


if __name__ == '__main__':
    main()
