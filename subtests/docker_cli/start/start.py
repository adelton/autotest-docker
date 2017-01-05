r"""
Summary
---------

Test output of docker start command

Operational Summary
----------------------

#. Create new container.
#. Wait till end of container command.
#. Try to start container.
#. Check if container was started.

Prerequisites
----------------

*  A remote registry server
"""

from autotest.client.shared import error
from dockertest.subtest import SubSubtest
from dockertest.output import OutputGood
from dockertest.dockercmd import AsyncDockerCmd, DockerCmd
from dockertest.containers import DockerContainers
from dockertest.output import DockerVersion
from dockertest.xceptions import DockerTestNAError
from dockertest.images import DockerImage
from dockertest import subtest
from dockertest import config


class DockerContainersRunOnly(DockerContainers):

    """
    DockerContainers remove size checking from DockerContainers.
    It takes lots of time. Only running containers.
    """

    #: This is probably test-subject related, be a bit more noisy
    verbose = True

    # private methods don't need docstrings
    def _get_container_list(self):  # pylint: disable=C0111
        return self.docker_cmd("ps --no-trunc",
                               self.timeout)


class start(subtest.SubSubtestCaller):
    config_section = 'docker_cli/start'


class start_base(SubSubtest):

    def initialize(self):
        super(start_base, self).initialize()
        config.none_if_empty(self.config)
        self.sub_stuff["conts_obj"] = DockerContainers(self)
        self.sub_stuff["con_ro_obj"] = DockerContainersRunOnly(self)

        self.sub_stuff["image_name"] = None
        self.sub_stuff["container"] = None
        self.sub_stuff["containers"] = []

    def run_once(self):
        super(start_base, self).run_once()
        # 1. Run with no options
        dkrcmd = AsyncDockerCmd(self, 'start',
                                self.complete_docker_command_line(),
                                self.config['docker_start_timeout'])
        self.loginfo("Starting container...")
        self.loginfo("Executing background command: %s" % dkrcmd.command)
        dkrcmd.execute()
        dkrcmd.wait(self.config['dkrcmd_waittime'])
        self.sub_stuff["dkrcmd"] = dkrcmd

    def complete_docker_command_line(self):
        cmds = []

        if self.config["docker_attach"]:
            cmds.append("-a")
        if self.config["docker_interactive"]:
            cmds.append("-i")

        cmds.append(self.sub_stuff["container"].long_id)

        self.sub_stuff["start_cmd"] = cmds

        return cmds

    def outputgood(self):
        skip = None
        if self.config["docker_attach"] or self.config["docker_interactive"]:
            skip = ['nonprintables_check']
        # Raise exception if problems found
        OutputGood(self.sub_stuff['dkrcmd'], skip=skip)

    def postprocess(self):
        super(start_base, self).postprocess()
        self.outputgood()
        cmdresult = self.sub_stuff['dkrcmd'].cmdresult
        self.failif_ne(cmdresult.exit_status, 0,
                       "Non-zero start exit status: %s"
                       % cmdresult)

    def cleanup(self):
        super(start_base, self).cleanup()
        # Auto-converts "yes/no" to a boolean

        if (self.config['remove_after_test'] and
                'containers' in self.sub_stuff):
            for cont in self.sub_stuff["containers"]:
                try:
                    cid = cont.long_id
                    self.sub_stuff["conts_obj"].kill_container_by_long_id(cid)
                    self.wait_for_container_death(cont)
                except (ValueError, KeyError):
                    pass  # Death/removal is the goal
                try:
                    self.sub_stuff["conts_obj"].remove_by_obj(cont)
                except (ValueError, KeyError):
                    pass  # Removal is the goal

    def wait_for_container_death(self, container_obj):
        cont_id = container_obj.long_id
        prep_changes = DockerCmd(self, "wait", [cont_id],
                                 self.config['docker_run_timeout'])

        results = prep_changes.execute()
        return results.exit_status

    @staticmethod
    def skip_if_docker_1_10():
        if DockerVersion().server.startswith("1.10"):
            raise DockerTestNAError("rhbz#1330224 will not be fixed in 1.10")


class short_term_app(start_base):
    config_section = 'docker_cli/start/short_term_app'
    check_if_cmd_finished = True

    def initialize(self):
        super(short_term_app, self).initialize()

        docker_name = DockerImage.full_name_from_defaults(self.config)
        # Private to this instance, outside of __init__
        prep_changes = DockerCmd(self, "run",
                                 ["-d", docker_name, self.config["run_cmd"]],
                                 self.config['docker_run_timeout'])

        results = prep_changes.execute()
        if results.exit_status:
            raise error.TestNAError("Problems during initialization of"
                                    " test: %s" % results)
        else:
            c_id = results.stdout.strip()
            cont = self.sub_stuff["conts_obj"].list_containers_with_cid(c_id)
            if cont == []:
                raise error.TestNAError("Problems during initialization of"
                                        " test: Failed to find container with"
                                        "id %s." % c_id)
            self.sub_stuff["container"] = cont[0]
            self.sub_stuff["containers"].append(self.sub_stuff["container"])

        if self.check_if_cmd_finished:
            self.wait_for_container_death(cont[0])
