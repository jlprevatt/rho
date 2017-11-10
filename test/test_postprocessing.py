# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""Unit tests for fact postprocessing"""

import unittest
from rho import postprocessing

# pylint: disable=missing-docstring


class TestProcessIdUJboss(unittest.TestCase):
    @staticmethod
    def run_func(output):
        return postprocessing.process_id_u_jboss(
            ['jboss.eap.jboss-user'],
            {'jboss_eap_id_jboss': output})

    def test_fact_not_requested(self):
        self.assertEqual(
            postprocessing.process_id_u_jboss([], None),
            {})

    def test_wrongly_skipped(self):
        res = self.run_func({'skipped': True})
        self.assertTrue('jboss.eap.jboss-user' in res and
                        res['jboss.eap.jboss-user'].startswith('Error:'),
                        msg=res['jboss.eap.jboss-user'])

    def test_user_found(self):
        self.assertEqual(
            self.run_func({'rc': 0, 'stdout_lines': []}),
            {'jboss.eap.jboss-user': "User 'jboss' present"})

    def test_no_such_user(self):
        self.assertEqual(
            self.run_func({'rc': 1,
                           'stdout_lines': ['id: jboss: no such user']}),
            {'jboss.eap.jboss-user': 'No user "jboss" found'})

    def test_unknown_error(self):
        res = self.run_func({'rc': 1,
                             'stdout_lines': ['id: something went wrong!']})

        self.assertTrue('jboss.eap.jboss-user' in res and
                        res['jboss.eap.jboss-user'].startswith('Error:'),
                        msg=res['jboss.eap.jboss-user'])


class TestProcessJbossCommonFiles(unittest.TestCase):
    @staticmethod
    def run_func(output):
        return postprocessing.process_jboss_eap_common_files(
            ['jboss.eap.common-files'],
            {'jboss_eap_common_files': output})

    def test_fact_not_requested(self):
        self.assertEqual(
            postprocessing.process_jboss_eap_common_files([], {}),
            {})

    def test_not_in_host_vars(self):
        res = postprocessing.process_jboss_eap_common_files(
            ['jboss.eap.common-files'], {})

        self.assertTrue(
            'jboss.eap.common-files' in res and
            res['jboss.eap.common-files'].startswith('Error:'),
            msg=res['jboss.eap.common-files'])

    def test_three_states(self):
        self.assertEqual(
            self.run_func({
                'results': [
                    {'item': 'dir1',
                     'skipped': True},
                    {'item': 'dir2',
                     'rc': 1},
                    {'item': 'dir3',
                     'rc': 0}]}),
            {'jboss.eap.common-files':
             'dir3 found'})


class TestProcessJbossEapProcesses(unittest.TestCase):
    @staticmethod
    def run_func(output):
        return postprocessing.process_jboss_eap_processes(
            ['jboss.eap.processes'],
            {'jboss.eap.processes': output})

    def test_no_processes(self):
        self.assertEqual(
            self.run_func({'rc': 1, 'stdout_lines': []}),
            {'jboss.eap.processes': 'No EAP processes found'})

    def test_found_processes(self):
        self.assertEqual(
            self.run_func({'rc': 0, 'stdout_lines': [1, 2, 3]}),
            {'jboss.eap.processes': '1 EAP processes found'})


class TestProcessJbossEapPackages(unittest.TestCase):
    @staticmethod
    def run_func(output):
        return postprocessing.process_jboss_eap_packages(
            ['jboss.eap.packages'],
            {'jboss.eap.packages': output})

    def test_nonzero_return_code(self):
        self.assertEqual(
            self.run_func({'rc': 1, 'stdout_lines': []}),
            {'jboss.eap.packages': 'Pipeline returned non-zero status'})

    def test_found_packages(self):
        self.assertEqual(
            self.run_func({'rc': 0, 'stdout_lines': ['a', 'b', 'c']}),
            {'jboss.eap.packages': '3 JBoss-related packages found'})

    def test_no_packages(self):
        self.assertEqual(
            self.run_func({'rc': 0, 'stdout_lines': []}),
            {'jboss.eap.packages': '0 JBoss-related packages found'})


class TestProcessRPMPackages(unittest.TestCase):

    def test_rpm_packages(self):
        # pylint: disable=C0301
        data = {'redhat-packages.results':
                    ["ghc-semigroups|0.8.5|3.el7|1506981888|Fedora Project|1480663695|buildhw-09.phx2.fedoraproject.org|ghc-semigroups-0.8.5-3.el7.src.rpm|BSD|Fedora Project|Mon 02 Oct 2017 06:04:48 PM EDT|Fri 02 Dec 2016 02:28:15 AM EST|(none)|RSA/SHA256, Fri 09 Dec 2016 01:17:53 AM EST, Key ID 6a2faea2352c64e5|(none)|RSA/SHA256, Fri 09 Dec 2016 01:17:53 AM EST, Key ID 6a2faea2352c64e5|",  # noqa: E501
                     "dhclient|4.2.5|58.el7|1500397510|Red Hat, Inc.|1494940069|x86-030.build.eng.bos.redhat.com|dhcp-4.2.5-58.el7.src.rpm|ISC|Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>|Tue 18 Jul 2017 01:05:10 PM EDT|Tue 16 May 2017 09:07:49 AM EDT|(none)|RSA/SHA256, Tue 16 May 2017 09:40:41 AM EDT, Key ID 199e2f91fd431d51|(none)|RSA/SHA256, Tue 16 May 2017 09:40:40 AM EDT, Key ID 199e2f91fd431d51|",  # noqa: E501
                     "setup|2.8.71|7.el7|1500397469|Red Hat, Inc.|1462364954|arm64-018.build.eng.bos.redhat.com|setup-2.8.71-7.el7.src.rpm|Public Domain|Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>|Tue 18 Jul 2017 01:04:29 PM EDT|Wed 04 May 2016 08:29:14 AM EDT|(none)|RSA/SHA256, Fri 23 Sep 2016 06:55:43 AM EDT, Key ID 199e2f91fd431d51|(none)|RSA/SHA256, Fri 23 Sep 2016 06:55:43 AM EDT, Key ID 199e2f91fd431d51|"],  # noqa: E501
                'redhat-packages.num_installed_packages': '',
                'redhat-packages.is_redhat': '',
                'redhat-packages.num_rh_packages': '',
                'redhat-packages.last_installed': '',
                'redhat-packages.last_built': '',
                'redhat-packages.gpg.num_installed_packages': '',
                'redhat-packages.gpg.is_redhat': '',
                'redhat-packages.gpg.num_rh_packages': '',
                'redhat-packages.gpg.last_installed': '',
                'redhat-packages.gpg.last_built': ''}
        facts = ['redhat-packages.num_installed_packages',
                 'redhat-packages.is_redhat',
                 'redhat-packages.num_rh_packages',
                 'redhat-packages.last_installed',
                 'redhat-packages.last_built',
                 'redhat-packages.gpg.num_installed_packages',
                 'redhat-packages.gpg.is_redhat',
                 'redhat-packages.gpg.num_rh_packages',
                 'redhat-packages.gpg.last_installed',
                 'redhat-packages.gpg.last_built']
        results = postprocessing.handle_redhat_packages(facts, data)
        self.assertIn('redhat-packages.num_installed_packages', results)
        self.assertEqual(results['redhat-packages.num_installed_packages'], 3)
        self.assertIn('redhat-packages.is_redhat', results)
        self.assertEqual(results['redhat-packages.is_redhat'], 'Y')
        self.assertIn('redhat-packages.num_rh_packages', results)
        self.assertEqual(results['redhat-packages.num_rh_packages'], 2)
        self.assertIn('redhat-packages.last_installed', results)
        self.assertEqual(results['redhat-packages.last_installed'],
                         'dhclient-4.2.5-58.el7 Installed: Tue 18'
                         ' Jul 2017 01:05:10 PM EDT')
        self.assertIn('redhat-packages.last_built', results)
        self.assertEqual(results['redhat-packages.last_built'],
                         'dhclient-4.2.5-58.el7 Built: Tue 16 May'
                         ' 2017 09:07:49 AM EDT')

        self.assertIn('redhat-packages.gpg.num_installed_packages', results)
        self.assertEqual(results['redhat-packages.gpg.num_installed_packages'],
                         3)
        self.assertIn('redhat-packages.gpg.is_redhat', results)
        self.assertEqual(results['redhat-packages.gpg.is_redhat'], 'Y')
        self.assertIn('redhat-packages.gpg.num_rh_packages', results)
        self.assertEqual(results['redhat-packages.gpg.num_rh_packages'], 2)
        self.assertIn('redhat-packages.gpg.last_installed', results)
        self.assertEqual(results['redhat-packages.gpg.last_installed'],
                         'dhclient-4.2.5-58.el7 Installed: Tue 18'
                         ' Jul 2017 01:05:10 PM EDT')
        self.assertIn('redhat-packages.gpg.last_built', results)
        self.assertEqual(results['redhat-packages.gpg.last_built'],
                         'dhclient-4.2.5-58.el7 Built: Tue 16 May'
                         ' 2017 09:07:49 AM EDT')

    def test_rpm_packages_no_rpm(self):
        data = {'redhat-packages.results': 'N/A (rpm not found)',
                'redhat-packages.num_installed_packages': '',
                'redhat-packages.is_redhat': '',
                'redhat-packages.num_rh_packages': '',
                'redhat-packages.last_installed': '',
                'redhat-packages.last_built': '',
                'redhat-packages.gpg.num_installed_packages': '',
                'redhat-packages.gpg.is_redhat': '',
                'redhat-packages.gpg.num_rh_packages': '',
                'redhat-packages.gpg.last_installed': '',
                'redhat-packages.gpg.last_built': ''}

        facts = ['redhat-packages.num_installed_packages',
                 'redhat-packages.is_redhat',
                 'redhat-packages.num_rh_packages',
                 'redhat-packages.last_installed',
                 'redhat-packages.last_built',
                 'redhat-packages.gpg.num_installed_packages',
                 'redhat-packages.gpg.is_redhat',
                 'redhat-packages.gpg.num_rh_packages',
                 'redhat-packages.gpg.last_installed',
                 'redhat-packages.gpg.last_built']
        results = postprocessing.handle_redhat_packages(facts, data)
        self.assertIn('redhat-packages.num_installed_packages', results)
        self.assertEqual(results['redhat-packages.num_installed_packages'], '')
        self.assertIn('redhat-packages.is_redhat', results)
        self.assertEqual(results['redhat-packages.is_redhat'], '')
        self.assertIn('redhat-packages.num_rh_packages', results)
        self.assertEqual(results['redhat-packages.num_rh_packages'], '')
        self.assertIn('redhat-packages.last_installed', results)
        self.assertEqual(results['redhat-packages.last_installed'], '')
        self.assertIn('redhat-packages.last_built', results)
        self.assertEqual(results['redhat-packages.last_built'], '')

        self.assertIn('redhat-packages.gpg.num_installed_packages', results)
        self.assertEqual(results['redhat-packages.gpg.num_installed_packages'],
                         '')
        self.assertIn('redhat-packages.gpg.is_redhat', results)
        self.assertEqual(results['redhat-packages.gpg.is_redhat'], '')
        self.assertIn('redhat-packages.gpg.num_rh_packages', results)
        self.assertEqual(results['redhat-packages.gpg.num_rh_packages'], '')
        self.assertIn('redhat-packages.gpg.last_installed', results)
        self.assertEqual(results['redhat-packages.gpg.last_installed'], '')
        self.assertIn('redhat-packages.gpg.last_built', results)
        self.assertEqual(results['redhat-packages.gpg.last_built'], '')


class TestProcessJbossLocateJbossModulesJar(unittest.TestCase):
    def run_expect_well_formed(self, output):
        val = postprocessing.process_jboss_eap_locate(
            [postprocessing.JBOSS_EAP_LOCATE_JBOSS_MODULES_JAR],
            {'jboss_eap_locate_jboss_modules_jar': output})

        self.assertIsInstance(val, dict)
        self.assertEqual(len(val), 1)
        self.assertIn(postprocessing.JBOSS_EAP_LOCATE_JBOSS_MODULES_JAR, val)

        return val[postprocessing.JBOSS_EAP_LOCATE_JBOSS_MODULES_JAR]

    # Most of the error handling is in
    # postprocessing.raw_output_present, which is tested elsewhere, so
    # we don't need to repeat those tests here.

    def test_success(self):
        self.assertEqual(
            self.run_expect_well_formed(
                {'rc': 0, 'stdout_lines': ['a', 'b', 'c']}),
            'a;b;c')

    def test_not_found(self):
        self.assertEqual(
            self.run_expect_well_formed(
                {'rc': 1, 'stdout_lines': []}),
            'jboss-modules.jar not found')

    def test_bad_output(self):
        self.assertEqual(
            self.run_expect_well_formed(
                {'rc': 1, 'stdout': "Command 'locate' not found",
                 'stdout_lines': ["Command 'locate' not found"]}),
            "Error code 1 running 'locate jboss-modules.jar': "
            "Command 'locate' not found")


class TestProcessJbossEapHome(unittest.TestCase):
    def test_one_dir(self):
        ls_result = [
            'appclient', 'docs', 'installation', 'LICENSE.txt', 'standalone',
            'welcome-content', 'bin', 'domain', 'JBossEULA.txt', 'modules',
            'Uninstaller', 'bundles', 'icons', 'jboss-modules.jar',
            'SHA256SUM', 'version.txt']
        cat_result = (
            'Red Hat JBoss Enterprise Application Platform - Version 6.4.0.GA')

        result = postprocessing.process_jboss_eap_home(
            [postprocessing.JBOSS_EAP_EAP_HOME],
            {'eap_home_candidates_ls': {
                'results': [
                    {'item': 'eap_home', 'rc': 0,
                     'stdout_lines': ls_result}]},
             'eap_home_candidates_version_txt': {
                 'results': [
                     {'item': 'eap_home', 'rc': 0,
                      'stdout': cat_result}]}})

        self.assertIn(postprocessing.JBOSS_EAP_EAP_HOME, result)
        dir_result = result[postprocessing.JBOSS_EAP_EAP_HOME]

        # pylint: disable=line-too-long
        self.assertEqual(dir_result,
                         'eap_home: eap_home contains appclient,standalone,JBossEULA.txt,modules,jboss-modules.jar,version.txt, Red Hat JBoss Enterprise Application Platform - Version 6.4.0.GA')  # noqa


class TestProcessFuseOnEap(unittest.TestCase):
    def test_success(self):
        ls_bin = ['fuseconfig.sh', 'fusepatch.sh']
        layers_conf = '#Tue Oct 24 16:22:35 EDT 2017\nlayers=fuse,soa\n'
        ls_layers = ['base', 'fuse', 'soa']

        result = postprocessing.process_fuse_on_eap(
            [postprocessing.JBOSS_FUSE_FUSE_ON_EAP],
            {'eap_home_candidates_bin': {
                'results': [
                    {'item': 'eap_home', 'rc': 0,
                     'stdout_lines': ls_bin}]},
             'eap_home_candidates_layers_conf': {
                 'results': [
                     {'item': 'eap_home', 'rc': 0,
                      'stdout': layers_conf}]},
             'eap_home_candidates_layers': {
                 'results': [
                     {'item': 'eap_home', 'rc': 0,
                      'stdout_lines': ls_layers}]}})

        self.assertIn(postprocessing.JBOSS_FUSE_FUSE_ON_EAP, result)
        dir_result = result[postprocessing.JBOSS_FUSE_FUSE_ON_EAP]

        # pylint: disable=line-too-long
        self.assertEqual(dir_result,
                         'eap_home: /bin=eap_home contains fuseconfig.sh,fusepatch.sh, /modules/layers.conf=#Tue Oct 24 16:22:35 EDT 2017\nlayers=fuse,soa, /modules/system/layers=eap_home contains fuse')  # noqa


class TestEscapeCharacters(unittest.TestCase):
    def test_string(self):
        data = {'key': 'abc\r\nde,f'}
        postprocessing.escape_characters(data)
        self.assertEqual(data['key'], 'abc de f')

    def test_unicode(self):
        data = {'key': u'abc\r\nde,f'}
        postprocessing.escape_characters(data)
        self.assertEqual(data['key'], u'abc de f')
