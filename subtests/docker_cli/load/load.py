"""
Summary
-------

Verify loading image from file works from static content.

Operational Summary
---------------------

#.  Verify static content doesn't already exist in repository
#.  Use docker load on existing tarball
#.  Verify expected ID exists.
#.  Remove loaded image
"""
import os
from dockertest import subtest
from dockertest.dockercmd import DockerCmd
from dockertest.images import DockerImages
from dockertest.config import get_as_list
from dockertest.output import mustpass
from dockertest.output import OutputGood
from dockertest.output import DockerVersion
from dockertest import xceptions


class load(subtest.Subtest):

    def initialize(self):
        super(load, self).initialize()
        self.stuff['di'] = di = DockerImages(self)
        img_id = self._test_id
        img_name = self.config['test_fqin'].strip()
        img_file = self.config['test_filename'].strip()
        if img_file[0] != '/':
            img_file = os.path.join(self.bindir,
                                    self.config['test_filename'])
        # image id is known for static content
        DockerCmd(self, 'rmi', [img_id]).execute()
        self.failif(img_id in di.list_imgs_ids(),
                    "Failed to remove test image with id %s" % img_id)
        self.failif(img_name in di.list_imgs_full_name(),
                    "Failed to remove test image with name %s" % img_name)
        self.stuff['dkrcmd'] = DockerCmd(self, 'load',
                                         ['--input', img_file])

    @property
    def _test_id(self):
        img_id = self.config['test_id']
        # FIXME: remove this once docker < 1.10 is eradicated
        try:
            DockerVersion().require_client("1.10")
        except xceptions.DockerTestNAError:
            img_id = self.config['test_id_old']
        return img_id.strip()

    def run_once(self):
        super(load, self).run_once()
        self.stuff['dkrcmd'].execute()

    def postprocess(self):
        super(load, self).postprocess()
        OutputGood(self.stuff['dkrcmd'].cmdresult)
        mustpass(self.stuff['dkrcmd'])
        img_id = self._test_id
        img_name = self.config['test_fqin']
        di = self.stuff['di']
        self.failif(img_id not in di.list_imgs_ids(),
                    "Failed to remove test image with id %s" % img_id)
        self.failif(img_name not in di.list_imgs_full_name(),
                    "Failed to remove test image with name %s" % img_name)

    def cleanup(self):
        super(load, self).cleanup()
        if self.config['remove_after_test']:
            preserve_fqins = get_as_list(self.config['preserve_fqins'])
            test_fqin = self.config['test_fqin']
            if test_fqin in preserve_fqins:
                return
            DockerCmd(self, 'rmi', ['--force', test_fqin]).execute()
