# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# At one point we had a bug where we added a new fact but forgot to
# add it to ALL_FACTS, so users couldn't select it. The way we define
# facts below is intended to make it impossible for that to happen
# again.

"""Defining the set of facts that Rho can scan for."""

import collections
import sys
from rho.utilities import log

ALWAYS_COLLECT = set()
SENSITIVE_FACTS = set()
DEFAULT_FACTS = set()
ALL_FACTS = set()

RHEL_FACTS = set()
JBOSS_FACTS = set()

# 'rho fact list' will print fact documentation in whatever order this
# dictionary's iterator returns them, so need to keep it sorted.
FACT_DOCS = collections.OrderedDict()


def expand_facts(fact_names):
    """Expand a list of facts with implicit facts and short names.

    :param fact_names: a list of fact names
    :returns: a set of facts to collect
    """

    facts_to_collect = set()

    for fact in fact_names:
        if fact == 'all':
            return ALL_FACTS

        if fact == 'default':
            facts_to_collect.update(DEFAULT_FACTS)
        elif fact == 'rhel':
            facts_to_collect.update(RHEL_FACTS)
        elif fact == 'jboss':
            facts_to_collect.update(JBOSS_FACTS)
        else:
            facts_to_collect.add(fact)

    if fact_names == []:
        facts_to_collect.update(DEFAULT_FACTS)

    facts_to_collect.update(ALWAYS_COLLECT)

    bad_facts = facts_to_collect.difference(ALL_FACTS)
    if bad_facts:
        log.error('Unknown facts requested: %s', ', '.join(sorted(bad_facts)))
        sys.exit(1)

    return facts_to_collect


# pylint: disable=too-many-arguments
def new_fact(fact_name, description, is_default=None,
             is_sensitive=False, always_collect=False,
             categories=None):
    """Define a new fact.

    :param fact_name: the name of the fact.
    :param description: a short description of the fact, for 'rho fact list'
        and the documentation.
    :param is_default: whether this fact should be scanned for by default.
    :param is_sensitive: whether this fact should be redacted by
        'rho fact hash'.
    :param always_collect: whether rho should always collect this fact.
    """

    if is_default is None:
        raise ValueError('new_fact: is_default must be set, but is not')

    ALL_FACTS.add(fact_name)
    if is_sensitive:
        SENSITIVE_FACTS.add(fact_name)
    if is_default:
        DEFAULT_FACTS.add(fact_name)
    if always_collect:
        ALWAYS_COLLECT.add(fact_name)

    FACT_DOCS[fact_name] = description

    # There's no point in categorizing a fact that we always collect.
    if always_collect:
        assert not categories

    if categories:
        for category in categories:
            category.add(fact_name)


new_fact('connection.host', 'The host address of the connection',
         is_default=True, is_sensitive=True, always_collect=True)
new_fact('connection.port', 'The port used for the connection',
         is_default=True, is_sensitive=True, always_collect=True)
new_fact('connection.uuid', 'A generated identifier for the connection',
         is_default=True, always_collect=True)
new_fact('cpu.bogomips', 'measurement of CPU speed made by the Linux kernel',
         is_default=True, categories=[RHEL_FACTS])
new_fact('cpu.count', 'number of processors',
         is_default=True, categories=[RHEL_FACTS])
new_fact('cpu.core_count', 'number of cores',
         is_default=True, categories=[RHEL_FACTS])
new_fact('cpu.cpu_family', 'cpu family',
         is_default=True, categories=[RHEL_FACTS])
new_fact('cpu.hyperthreading', 'Whether cpu is hyperthreaded',
         is_default=True, categories=[RHEL_FACTS])
new_fact('cpu.model_name', 'cpu model name',
         is_default=True, categories=[RHEL_FACTS])
new_fact('cpu.model_ver', 'cpu model version',
         is_default=True, categories=[RHEL_FACTS])
new_fact('cpu.socket_count', 'number of sockets',
         is_default=True, categories=[RHEL_FACTS])
new_fact('cpu.vendor_id', 'cpu vendor name',
         is_default=True, categories=[RHEL_FACTS])
new_fact('date.anaconda_log', '/root/anaconda-ks.cfg modified time',
         is_default=True, categories=[RHEL_FACTS])
new_fact('date.date', 'date',
         is_default=True, categories=[RHEL_FACTS])
new_fact('date.filesystem_create',
         'uses tune2fs -l on the / filesystem dev found using mount',
         is_default=True, categories=[RHEL_FACTS])
new_fact('date.machine_id', "/etc/machine-id modified time'",
         is_default=True, categories=[RHEL_FACTS])
new_fact('date.yum_history', 'dates from yum history',
         is_default=True, categories=[RHEL_FACTS])
new_fact('dmi.bios-vendor', 'bios vendor name',
         is_default=True, categories=[RHEL_FACTS])
new_fact('dmi.bios-version', 'bios version info',
         is_default=True, categories=[RHEL_FACTS])
new_fact('dmi.processor-family', 'processor family',
         is_default=True, categories=[RHEL_FACTS])
new_fact('dmi.system-manufacturer', 'system manufacturer',
         is_default=True, categories=[RHEL_FACTS])
new_fact('etc-issue.etc-issue', 'contents of /etc/issue (or equivalent)',
         is_default=True, categories=[RHEL_FACTS])
new_fact('etc_release.name', 'name of the release',
         is_default=True, categories=[RHEL_FACTS])
new_fact('etc_release.release', 'release information',
         is_default=True, categories=[RHEL_FACTS])
new_fact('etc_release.version', 'release version',
         is_default=True, categories=[RHEL_FACTS])
new_fact('instnum.instnum', 'installation number',
         is_default=True, categories=[RHEL_FACTS])
new_fact('jboss.brms.drools-core-ver', 'Drools version', is_default=False)
new_fact('jboss.brms.kie-api-ver', 'KIE API version', is_default=False)
new_fact('jboss.brms.kie-war-ver', 'KIE runtime version', is_default=False)
new_fact('jboss.eap.common-files',
         'Presence of common files and directories for JBoss EAP',
         is_default=True, categories=[JBOSS_FACTS])
new_fact('jboss.eap.deploy-dates',
         'List of deployment dates of JBoss EAP installations',
         is_default=False)
new_fact('jboss.eap.init-files',
         'Find system services that look JBoss-related',
         is_default=True)
new_fact('jboss.eap.installed-versions',
         'List of installed versions of JBoss EAP',
         is_default=False)
new_fact('jboss.eap.locate-jboss-modules-jar',
         'Use locate to find jboss-modules.jar',
         is_default=True, categories=[JBOSS_FACTS])
new_fact('jboss.eap.jboss-user', "Whether a user called 'jboss' exists",
         is_default=True, categories=[JBOSS_FACTS])
new_fact('jboss.eap.packages', 'Installed RPMs that look like JBoss',
         is_default=True, categories=[JBOSS_FACTS])
new_fact('jboss.eap.processes', 'Running processes that look like JBoss',
         is_default=True, categories=[JBOSS_FACTS])
new_fact('jboss.eap.running-paths', 'Paths of running installs of JBoss EAP',
         is_default=True, categories=[JBOSS_FACTS])
new_fact('jboss.fuse.activemq-ver', 'ActiveMQ version', is_default=False)
new_fact('jboss.fuse.camel-ver', 'Camel version', is_default=False)
new_fact('jboss.fuse.cxf-ver', 'CXF version', is_default=False)
new_fact('redhat-packages.certs', 'the list of Red Hat certificates found',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.gpg.is_redhat',
         'determines if package is a Red Hat package filtered by GPG keys',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.gpg.last_installed',
         'last installed package filtered by GPG keys',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.gpg.last_built',
         'last built package filtered by GPG keys',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.gpg.num_rh_packages',
         'number of Red Hat packages filtered by GPG keys',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.gpg.num_installed_packages',
         'number of installed packages filtered by GPG keys',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.is_redhat',
         'determines if package is a Red Hat package',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.last_installed', 'last installed package',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.last_built', 'last built package',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.num_rh_packages', 'number of Red Hat packages',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-packages.num_installed_packages',
         'number of installed packages',
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-release.name',
         "name of package that provides 'redhat-release'",
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-release.release',
         "release of package that provides 'redhat-release'",
         is_default=True, categories=[RHEL_FACTS])
new_fact('redhat-release.version',
         "version of package that provides 'redhat-release'",
         is_default=True, categories=[RHEL_FACTS])
new_fact('subman.consumed',
         'consumed SKUs from subscription manager',
         is_default=True, categories=[RHEL_FACTS])
new_fact('subman.cpu.core(s)_per_socket',
         'cpu cores per socket from subscription manager',
         is_default=True, categories=[RHEL_FACTS])
new_fact('subman.cpu.cpu(s)', 'cpus from subscription manager',
         is_default=True, categories=[RHEL_FACTS])
new_fact('subman.cpu.cpu_socket(s)', 'cpu sockets from subscription manager',
         is_default=True, categories=[RHEL_FACTS])
new_fact('subman.has_facts_file',
         'Whether subscription manager has a facts file',
         is_default=True, categories=[RHEL_FACTS])
new_fact('subman.virt.is_guest',
         'Whether is a virtual guest from subscription manager',
         is_default=True, categories=[RHEL_FACTS])
new_fact('subman.virt.host_type',
         'Virtual host type from subscription manager',
         is_default=True, categories=[RHEL_FACTS])
new_fact('subman.virt.uuid', 'Virtual host uuid from subscription manager',
         is_default=True, categories=[RHEL_FACTS])
new_fact('systemid.system_id', 'Red Hat Network System ID',
         is_default=True, categories=[RHEL_FACTS])
new_fact('systemid.username', 'Red Hat Network username',
         is_default=True, categories=[RHEL_FACTS])
new_fact('uname.all', 'uname -a (all)',
         is_default=True, is_sensitive=True, categories=[RHEL_FACTS])
new_fact('uname.hardware_platform', 'uname -i (hardware_platform)',
         is_default=True, categories=[RHEL_FACTS])
new_fact('uname.hostname', 'uname -n (hostname)',
         is_default=True, is_sensitive=True, categories=[RHEL_FACTS])
new_fact('uname.kernel', 'uname -r (kernel)',
         is_default=True, categories=[RHEL_FACTS])
new_fact('uname.os', 'uname -s (os)',
         is_default=True, categories=[RHEL_FACTS])
new_fact('uname.processor', 'uname -p (processor)',
         is_default=True, categories=[RHEL_FACTS])
new_fact('virt.num_guests', 'the number of virtualized guests',
         is_default=True, categories=[RHEL_FACTS])
new_fact('virt.num_running_guests', 'the number of running virtualized guests',
         is_default=True, categories=[RHEL_FACTS])
new_fact('virt.type', 'type of virtual system',
         is_default=True, categories=[RHEL_FACTS])
new_fact('virt.virt', 'host, guest, or baremetal',
         is_default=True, categories=[RHEL_FACTS])
new_fact('virt-what.type', 'What type of virtualization a system is running',
         is_default=True, categories=[RHEL_FACTS])
