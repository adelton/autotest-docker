r"""
Summary
---------

Negative test, verify cannot run second container with same name.

Operational Summary
----------------------

#. Run a container with a certain name
#. Run a container with a certain name again
#. Fail to run a container again
"""

from autotest.client import utils
from dockertest import subtest
from dockertest.output import mustpass
from dockertest.dockercmd import DockerCmd
from dockertest.images import DockerImage
from dockertest.output import OutputGood
from dockertest.config import get_as_list


class run_twice(subtest.Subtest):
    config_section = 'docker_cli/run_twice'

    def initialize(self):
        super(run_twice, self).initialize()
        name = self.stuff['container_name'] = utils.generate_random_string(12)
        subargs = ['--name=%s' % name]
        fin = DockerImage.full_name_from_defaults(self.config)
        subargs.append(fin)
        subargs.append('/bin/bash')
        subargs.append('-c')
        cmd = '\'echo test\''
        subargs.append(cmd)
        self.stuff['subargs'] = subargs
        self.stuff['cmdresults'] = []
        self.stuff['2nd_cmdresults'] = []

    def run_once(self):
        super(run_twice, self).run_once()
        nfdc = DockerCmd(self, 'run', self.stuff['subargs'])
        self.stuff['cmdresults'].append(mustpass(nfdc.execute()))
        dc = DockerCmd(self, 'run', self.stuff['subargs'])
        self.stuff['2nd_cmdresults'].append(dc.execute())

    def postprocess(self):
        super(run_twice, self).postprocess()
        for cmdresult in self.stuff['cmdresults']:
            self.loginfo("command: '%s'" % cmdresult.command)
            outputgood = OutputGood(cmdresult, skip=['nonprintables_check'])
            self.failif(not outputgood, str(outputgood))
        for cmdresult in self.stuff['2nd_cmdresults']:
            self.loginfo("command: '%s'" % cmdresult.command)
            outputgood = OutputGood(cmdresult, ignore_error=True,
                                    skip=['error_check'])
            self.failif(cmdresult.exit_status == 0, str(outputgood))
            if cmdresult.exit_status != 0:
                self.logerror("Intend to fail:\n%s" % cmdresult.stderr.strip())

    def cleanup(self):
        super(run_twice, self).cleanup()
        if self.config['remove_after_test']:
            preserve_cnames = get_as_list(self.config['preserve_cnames'])
            cname = self.stuff['container_name']
            if cname not in preserve_cnames:
                DockerCmd(self, 'rm',
                          ['--force', '--volumes', cname]).execute()
