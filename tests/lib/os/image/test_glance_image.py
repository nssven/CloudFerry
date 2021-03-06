# Copyright (c) 2014 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the License);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an AS IS BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and#
# limitations under the License.

import mock

from cloudferry.lib.os.image import glance_image
from tests import test


FAKE_CONFIG = {
    'dst': {
        'user': 'fake_user',
        'password': 'fake_password',
        'tenant': 'fake_tenant',
        'region': None,
        'host': '1.1.1.1',
        'ssh_host': '1.1.1.10',
        'ssh_user': 'fake_user',
        'cacert': '',
        'insecure': False,
        'endpoint_type': 'privateURL'
    },
    'migrate': {
        'retry': '7',
        'time_wait': 5,
        'image_save_timeout': 1
    }
}


class FakeUser(object):
    def __init__(self):
        self.name = 'fake_user_name'


class GlanceImageTestCase(test.TestCase):

    def setUp(self):
        test.TestCase.setUp(self)

        self.override_config(FAKE_CONFIG)

        self.glance_mock_client = mock.MagicMock()
        self.glance_mock_client().images.data().iterable = 'fake_resp_1'

        m = mock.patch('glanceclient.v1.client.Client',
                       new=self.glance_mock_client)
        self.glance_client_patch = m.start()
        self.addCleanup(m.stop)
        self.identity_mock = mock.Mock()
        self.identity_mock.get_endpoint_by_service_type = mock.Mock(
            return_value="http://192.168.1.2:9696/v2")
        fake_user = FakeUser()
        self.identity_mock.try_get_user_by_id = mock.Mock(
            return_value=fake_user)
        self.identity_mock.try_get_tenant_name_by_id = mock.Mock(
            return_value="fake_tenant_name")
        self.identity_mock.keystone_client.users.list = mock.Mock(
            return_value=[])
        self.image_mock = mock.Mock()

        self.fake_cloud = mock.Mock()
        self.fake_cloud.position = 'dst'
        self.fake_cloud.resources = dict(identity=self.identity_mock,
                                         image=self.image_mock)
        self.fake_cloud.mysql_connector = mock.MagicMock()
        self.fake_cloud.config = self.cloud_config('dst')

        self.glance_image = glance_image.GlanceImage(self.fake_cloud.config,
                                                     self.fake_cloud)

        self.fake_image_1 = mock.MagicMock()

        values_dict = {
            'id': 'fake_image_id_1',
            'name': 'fake_image_name_1',
            'status': 'active',
            'checksum': 'fake_shecksum_1',
            'owner': 'fake_tenant_id',
            'container_format': 'bare',
            'disk_format': 'qcow2',
            'is_public': True,
            'protected': False,
            'size': 1024,
            'properties': {},
            'deleted': False,
        }
        for k, w in values_dict.items():
            setattr(self.fake_image_1, k, w)
        self.fake_image_1.to_dict = mock.Mock(return_value=values_dict)
        self.fake_image_1.deleted = False

        self.fake_image_2 = mock.Mock()
        self.fake_image_2.name = 'fake_image_name_2'
        self.fake_image_2.deleted = False

        self.fake_input_info = {'images': {}}

        self.fake_result_info = {
            'images': {
                'fake_image_id_1': {'image': {'checksum': 'fake_shecksum_1',
                                              'container_format': 'bare',
                                              'disk_format': 'qcow2',
                                              'id': 'fake_image_id_1',
                                              'is_public': True,
                                              'location': None,
                                              'owner': 'fake_tenant_id',
                                              'owner_name': 'fake_tenant_name',
                                              'name': 'fake_image_name_1',
                                              'protected': False,
                                              'size': 1024,
                                              'resource': self.image_mock,
                                              'members': {},
                                              'properties': {},
                                              'copy_from': None,
                                              'min_disk': None,
                                              'min_ram': None,
                                              'store': None,
                                              'deleted': False},
                                    'meta': {'img_loc': None}}},
            'tags': {},
            'members': {}
        }

    def test_get_glance_client(self):
        fake_endpoint = 'fake_endpoint'
        fake_auth_token = 'fake_auth_token'
        self.identity_mock.get_endpoint_by_service_type.return_value = (
            fake_endpoint)
        self.identity_mock.get_auth_token_from_user.return_value = (
            fake_auth_token)

        gl_client = self.glance_image.get_client()
        mock_calls = [mock.call(fake_endpoint, token=fake_auth_token,
                                insecure=self.fake_cloud.config.cloud.insecure,
                                session=None)]

        self.glance_mock_client.assert_has_calls(mock_calls)
        self.assertEqual(self.glance_mock_client(), gl_client)

    def test_get_image_list(self):
        fake_images = [self.fake_image_1, self.fake_image_2]
        self.glance_mock_client().images.list.return_value = fake_images

        images_list = self.glance_image.get_image_list()
        self.glance_mock_client().images.list.assert_called_once_with(
            filters={'is_public': None})
        self.assertEquals(fake_images, images_list)

    def test_create_image(self):
        self.glance_image.create_image(name='fake_image_name',
                                       data='fake_data')
        test_args = {'name': 'fake_image_name',
                     'data': 'fake_data'}

        self.glance_mock_client().images.create.assert_called_once_with(
            **test_args)

    def test_delete_image(self):
        fake_image_id = 'fake_image_id_1'
        self.glance_image.delete_image(fake_image_id)

        self.glance_mock_client().images.update.assert_called_once_with(
            fake_image_id, protected=False)
        self.glance_mock_client().images.delete.assert_called_once_with(
            fake_image_id)

    def test_get_image_by_id(self):
        self.glance_mock_client().images.get.return_value = self.fake_image_1

        self.assertEquals(self.fake_image_1,
                          self.glance_image.get_image_by_id('fake_image_id_1'))

    def test_get_image_by_name(self):
        fake_images = [self.fake_image_1, self.fake_image_2]
        self.glance_mock_client().images.list.return_value = fake_images

        self.assertEquals(
            self.fake_image_1,
            self.glance_image.get_image_by_name('fake_image_name_1'))

    def test_get_image(self):
        fake_images = [self.fake_image_1, self.fake_image_2]
        self.glance_mock_client().images.list.return_value = fake_images

        self.assertEquals(self.fake_image_1,
                          self.glance_image.get_image('fake_image_id_1'))

        self.assertEquals(self.fake_image_2,
                          self.glance_image.get_image('fake_image_name_2'))

    def test_get_image_status(self):
        self.glance_mock_client().images.get.return_value = self.fake_image_1

        self.assertEquals(self.fake_image_1.status,
                          self.glance_image.get_image_status(
                              'fake_image_id_1'))

    def test_get_ref_image(self):
        self.glance_mock_client().images.data.return_value = 'fake_resp_1'

        self.assertEquals('fake_resp_1',
                          self.glance_image.get_ref_image('fake_image_id_1'))

    def test_get_image_checksum(self):
        self.glance_mock_client().images.get.return_value = self.fake_image_1

        self.assertEquals(self.fake_image_1.checksum,
                          self.glance_image.get_image_checksum(
                              'fake_image_id_1'))

    def test_make_image_info(self):
        info = self.glance_image.make_image_info(self.fake_image_1,
                                                 self.fake_input_info)

        self.assertEqual({"images": self.fake_result_info["images"]}, info)

    def test_make_image_info_no_image(self):
        info = self.glance_image.make_image_info(self.fake_image_1,
                                                 self.fake_input_info)

        self.assertEqual(self.fake_input_info, info)

    def test_read_info_id(self):
        fake_images = [self.fake_image_1, self.fake_image_2]
        self.glance_mock_client().images.list.return_value = fake_images

        info = self.glance_image.read_info(image_id='fake_image_id_1')
        self.assertEqual(self.fake_result_info, info)

    def test_read_info_name(self):
        fake_images = [self.fake_image_1, self.fake_image_2]
        self.glance_mock_client().images.list.return_value = fake_images

        info = self.glance_image.read_info(image_name='fake_image_name_1')
        self.assertEqual(self.fake_result_info, info)

    def test_read_info_list(self):
        fake_images = [self.fake_image_1, self.fake_image_2]
        self.glance_mock_client().images.list.return_value = fake_images

        info = self.glance_image.read_info(images_list=['fake_image_name_1'])
        self.assertEqual(self.fake_result_info, info)

    def test_read_info_default(self):
        fake_images = [self.fake_image_1]
        self.glance_mock_client().images.list.return_value = fake_images

        info = self.glance_image.read_info()
        self.assertEqual(self.fake_result_info, info)

    def test_get_matching_image_positive_match_uuid(self):
        fake_images = [self.fake_image_1, self.fake_image_2]
        self.glance_mock_client().images.list.return_value = fake_images

        img = self.glance_image.get_matching_image(
            uuid=self.fake_image_1.id, checksum='mismatch_checksum',
            size=2048, name='mismatch_name')
        self.assertEqual(self.fake_image_1, img)

    def test_get_matching_image_positive_mismatch_uuid(self):
        fake_images = [self.fake_image_1, self.fake_image_2]
        self.glance_mock_client().images.list.return_value = fake_images

        img = self.glance_image.get_matching_image(
            uuid='mismatching', checksum=self.fake_image_1.checksum,
            size=self.fake_image_1.size, name=self.fake_image_1.name)
        self.assertEqual(self.fake_image_1, img)

    def test_get_matching_image_negative(self):
        fake_images = [self.fake_image_1, self.fake_image_2]
        self.glance_mock_client().images.list.return_value = fake_images

        img = self.glance_image.get_matching_image(
            uuid='mismatching', checksum='mismatch_checksum',
            size=2048, name='mismatch_name')
        self.assertEqual(None, img)
