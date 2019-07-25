import unittest

from see.context.resources.resources import Resources


class ImageTest(unittest.TestCase):
    def test_image_property(self):
        resources = Resources('foo', {'disk': {'image': {'name': 'bar',
                                                         'provider': 'see.image_providers.DummyProvider',
                                                         'provider_configuration': {
                                                             'path': '/foo'
                                                         }}}})

        assert resources.provider_image == '/foo/bar'

    def test_image_backwards_compatibility(self):
        image_path = '/foo/bar'
        resources = Resources('foo', {'disk': {'image': image_path}})

        assert image_path == resources.provider_image
