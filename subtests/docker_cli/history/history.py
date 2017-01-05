"""
Summary
----------
Test that checks the ``docker`` history command.

Operational Summary
----------------------

#. Prepare new image name.
#. Make changes in image by docker run
#. Make changes in image by docker run [dockerand_data_prepare_cmd].
#. Get docker history using docker image history.
#. check if image history is correct.
"""

import time
from autotest.client import utils
from dockertest.subtest import SubSubtest
from dockertest.images import DockerImages
from dockertest.images import DockerImage
from dockertest.containers import DockerContainers
from dockertest.output import OutputGood
from dockertest.dockercmd import AsyncDockerCmd, DockerCmd
from dockertest import subtest
from dockertest import config
from dockertest import xceptions


class history(subtest.SubSubtestCaller):
    config_section = 'docker_cli/history'


class history_base(SubSubtest):

    def check_image_exists(self, full_name):
        di = DockerImages(self)
        return di.list_imgs_with_full_name(full_name)

    def initialize(self):
        super(history_base, self).initialize()
        config.none_if_empty(self.config)
        dimgs = DockerImages(self)

        self.sub_stuff["containers"] = []
        self.sub_stuff["images"] = []

        new_img_name = dimgs.get_unique_name('1')
        self.sub_stuff["new_image_name"] = new_img_name

        new_img_name2 = dimgs.get_unique_name('2')
        self.sub_stuff["new_image_name2"] = new_img_name2

        self.sub_stuff['rand_data'] = utils.generate_random_string(8)
        cmd_with_rand = (self.config['docker_data_prepare_cmd']
                         % self.sub_stuff['rand_data'])

        fqin = DockerImage.full_name_from_defaults(self.config)
        # create new image in history
        self.create_image(fqin, new_img_name, cmd_with_rand)
        self.sub_stuff["images"].append(new_img_name)
        # create new image in history
        self.create_image(new_img_name, new_img_name2, cmd_with_rand)
        self.sub_stuff["images"].append(new_img_name2)

    def run_once(self):
        super(history_base, self).run_once()
        dkrcmd = AsyncDockerCmd(self, 'history', self.complete_history_cmd(),
                                self.config['docker_history_timeout'])
        self.loginfo("Executing background command: %s" % dkrcmd)
        dkrcmd.execute()
        while not dkrcmd.done:
            self.loginfo("historyting...")
            time.sleep(3)
        self.sub_stuff["cmdresult"] = dkrcmd.wait()

    def complete_history_cmd(self):
        repo_addr = self.sub_stuff["new_image_name2"]

        cmd = []
        cmd.append(repo_addr)
        self.sub_stuff["history_cmd"] = cmd
        return cmd

    def postprocess(self):
        super(history_base, self).postprocess()
        # Raise exception if problems found
        expect = self.config["docker_expected_exit_status"]
        OutputGood(self.sub_stuff['cmdresult'], ignore_error=(expect != 0),
                   skip=['nonprintables_check'])
        self.failif_ne(self.sub_stuff['cmdresult'].exit_status, expect,
                       "Exit status")

        if expect == 0:
            new_img_name = self.sub_stuff["new_image_name"]
            new_img_name2 = self.sub_stuff["new_image_name2"]
            base_img_name = DockerImage.full_name_from_defaults(self.config)

            self.failif(base_img_name in self.sub_stuff['cmdresult'].stdout,
                        "Unable find image name %s in image history: %s" %
                        (base_img_name,
                         self.sub_stuff['cmdresult'].stdout))

            self.failif(new_img_name in self.sub_stuff['cmdresult'].stdout,
                        "Unable find image name %s in image history: %s" %
                        (new_img_name,
                         self.sub_stuff['cmdresult'].stdout))

            self.failif(new_img_name2 in self.sub_stuff['cmdresult'].stdout,
                        "Unable find image name %s in image history: %s" %
                        (new_img_name2,
                         self.sub_stuff['cmdresult'].stdout))

    def cleanup(self):
        super(history_base, self).cleanup()
        if self.config['remove_after_test']:
            dc = DockerContainers(self)
            dc.clean_all(self.sub_stuff.get("containers"))
            di = DockerImages(self)
            di.clean_all(self.sub_stuff.get("images"))

    def create_image(self, old_name, new_name, cmd):
        prep_changes = DockerCmd(self, "run",
                                 ["--name=%s" % new_name, old_name, cmd],
                                 self.config['docker_history_timeout'])

        results = prep_changes.execute()
        if results.exit_status:
            raise xceptions.DockerTestNAError("Problems during "
                                              "initialization of"
                                              " test: %s", results)
        else:
            self.sub_stuff["containers"].append(new_name)

        prep_changes = DockerCmd(self, "commit", [new_name, new_name],
                                 self.config['docker_history_timeout'])

        results = prep_changes.execute()
        if results.exit_status:
            raise xceptions.DockerTestNAError("Problems during "
                                              "initialization of"
                                              " test: %s", results)
