import os
import json
from datetime import datetime

from django.core.management import call_command
from django.conf import settings

import responses

from olympia import amo
from olympia.amo.tests import addon_factory, TestCase, user_factory
from olympia.blocklist.management.commands import import_blocklist

from ..models import Block


# This is a fragment of the actual json blocklist file
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
blocklist_file = os.path.join(TESTS_DIR, 'blocklists', 'blocklist.json')
with open(blocklist_file) as file_object:
    blocklist_json = json.loads(file_object.read())


class TestImportBlocklist(TestCase):

    def setUp(self):
        responses.add(
            responses.GET,
            import_blocklist.Command.KINTO_JSON_BLOCKLIST_URL,
            json=blocklist_json)
        self.task_user = user_factory(id=settings.TASK_USER_ID)

    def test_empty(self):
        """ Test nothing is added if none of the guids match - any nothing
        fails.
        """
        addon_factory()
        assert Block.objects.count() == 0
        call_command('import_blocklist')
        assert Block.objects.count() == 0

    def test_regex(self):
        """ Test regex style "guids" are parsed and expanded to blocks."""
        addon_factory(guid='_qdMembers_@extmys.mysearch.com')
        addon_factory(guid='_r4Members_@install.salah-time.com')
        addon_factory(guid='{90ac1d06-caf8-46b9-9325-59c82190b687}')
        addon_factory()
        call_command('import_blocklist')
        assert Block.objects.count() == 3
        blocks = list(Block.objects.all())
        this_block = blocklist_json['data'][0]
        assert blocks[0].guid == '_qdMembers_@extmys.mysearch.com'
        assert blocks[1].guid == '_r4Members_@install.salah-time.com'
        assert blocks[2].guid == '{90ac1d06-caf8-46b9-9325-59c82190b687}'
        # the rest of the metadata should be the same
        for block in blocks:
            assert block.url == this_block['details']['bug']
            assert block.reason == this_block['details']['why']
            assert block.min_version == (
                this_block['versionRange'][0]['minVersion'])
            assert block.max_version == (
                this_block['versionRange'][0]['maxVersion'])
            assert block.kinto_id == '*' + this_block['id']
            assert block.include_in_legacy
            assert block.modified == datetime(2019, 11, 29, 22, 22, 46, 785000)

    def test_single_guid(self):
        addon_factory(guid='{99454877-875a-473e-a0c7-03ab910a8461}')
        addon_factory(guid='Stark-vpn.5.14@firefox.com')
        addon_factory()
        call_command('import_blocklist')
        assert Block.objects.count() == 2
        blocks = list(Block.objects.all())

        assert blocks[0].guid == '{99454877-875a-473e-a0c7-03ab910a8461}'
        assert blocks[0].url == blocklist_json['data'][1]['details']['bug']
        assert blocks[0].reason == blocklist_json['data'][1]['details']['why']
        assert blocks[0].min_version == (
            blocklist_json['data'][1]['versionRange'][0]['minVersion'])
        assert blocks[0].max_version == (
            blocklist_json['data'][1]['versionRange'][0]['maxVersion'])
        assert blocks[0].kinto_id == blocklist_json['data'][1]['id']
        assert blocks[0].include_in_legacy
        assert blocks[0].modified == datetime(2019, 11, 29, 15, 32, 56, 477000)

        assert blocks[1].guid == 'Stark-vpn.5.14@firefox.com'
        assert blocks[1].url == blocklist_json['data'][2]['details']['bug']
        assert blocks[1].reason == blocklist_json['data'][2]['details']['why']
        assert blocks[1].min_version == (
            blocklist_json['data'][2]['versionRange'][0]['minVersion'])
        assert blocks[1].max_version == (
            blocklist_json['data'][2]['versionRange'][0]['maxVersion'])
        assert blocks[1].kinto_id == blocklist_json['data'][2]['id']
        assert blocks[1].include_in_legacy
        assert blocks[1].modified == datetime(2019, 11, 22, 16, 49, 58, 416000)

    def test_target_application(self):
        fx_addon = addon_factory(
            guid='mozilla_cc2.2@internetdownloadmanager.com')
        # Block only for Thunderbird
        addon_factory(guid='{0D2172E4-C5AE-465A-B80D-53A840275B5E}')

        addon_factory()
        call_command('import_blocklist')
        assert Block.objects.count() == 1
        this_block = blocklist_json['data'][5]
        assert (
            this_block['versionRange'][0]['targetApplication'][0]['guid'] ==
            amo.FIREFOX.guid)
        assert Block.objects.get().guid == fx_addon.guid

    def test_bracket_escaping(self):
        """Some regexs don't escape the {} which is invalid in mysql regex.
        Check we escape it correctly."""
        addon1 = addon_factory(guid='{f0af464e-5167-45cf-9cf0-66b396d1918c}')
        addon2 = addon_factory(guid='{01e86e69-a2f8-48a0-b068-83869bdba3d0}')

        addon_factory()
        call_command('import_blocklist')
        assert Block.objects.count() == 2
        blocks = list(Block.objects.all())
        this_block = blocklist_json['data'][3]
        assert blocks[0].guid == addon1.guid
        assert blocks[1].guid == addon2.guid
        # the rest of the metadata should be the same
        for block in blocks:
            assert block.url == this_block['details']['bug']
            assert block.reason == this_block['details']['why']
            assert block.min_version == (
                this_block['versionRange'][0]['minVersion'])
            assert block.max_version == (
                this_block['versionRange'][0]['maxVersion'])
            assert block.kinto_id == '*' + this_block['id']
            assert block.include_in_legacy
