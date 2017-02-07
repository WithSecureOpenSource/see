import unittest

from see.context.resources.resources import Resources


class ImageTest(unittest.TestCase):
    def test_image_property(self):
        image_path = '/foo/bar'
        resources = Resources('foo', {'disk': {'image': {'uri': image_path,
                                                         'provider': 'see.image_providers.DummyProvider'}}})

        assert image_path == resources.provider_image

    def test_image_backwards_compatibility(self):
        image_path = '/foo/bar'
        resources = Resources('foo', {'disk': {'image': image_path}})

        assert image_path == resources.provider_image
