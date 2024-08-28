from django.test import TestCase, Client
from .models import DockerImage, DockerImageVersion, DockerImageVersionContents
from cireports.models import Package, PackageRevision, Categories
from datetime import datetime


class BaseSetUpTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = Package.objects.create(name="ERICtest_CXP1234567")
        cls.category = Categories.objects.create(name="sw")
        cls.package_revision = PackageRevision.objects.create(package=cls.package,
                                                              date_created=datetime.now(),
                                                              autodrop="latest.Maintrack",
                                                              last_update=datetime.now(),
                                                              category=cls.category,
                                                              version="1.12.3")
        cls.image = DockerImage.objects.create(name="test_image")
        cls.image_version = DockerImageVersion.objects.create(image=cls.image, version="1234")
        cls.image_version_contents = DockerImageVersionContents.objects.create(image_version=cls.image_version,
                                                                               package_revision=cls.package_revision)

    @classmethod
    def tearDownClass(cls):
        cls.package.delete()
        cls.category.delete()
        cls.package_revision.delete()
        cls.image.delete()
        cls.image_version.delete()
        cls.image_version_contents.delete()


class ModelTest(BaseSetUpTest):
    def test_docker_image_model(self):
        self.assertTrue(isinstance(self.image, DockerImage))
        self.assertEqual(self.image.__unicode__(), self.image.name)

    def test_docker_image_version_model(self):
        self.assertTrue(isinstance(self.image_version, DockerImageVersion))
        self.assertEqual(self.image_version.__unicode__(), "%s-%s" % (self.image_version.image.name,
                                                                      self.image_version.version))

    def test_docker_image_version_contents_model(self):
        self.assertTrue(isinstance(self.image_version_contents, DockerImageVersionContents))
        self.assertEqual(self.image_version_contents.__unicode__(),
                         "%s->%s" % (self.image_version_contents.image_version,
                                     self.image_version_contents.package_revision))


class ViewTest(BaseSetUpTest):
    def setUp(self):
        self.client_stub = Client()

    def test_fast_commit_post_success(self):
        response = self.client_stub.post('/api/fastcommit/images',
                                         data='{"package_revision": [{"package": "ERICtest_CXP1234567", '
                                              '"version": "1.12.3"}], '
                                              '"image_version": {"image": {"name": "test"}, '
                                              '"version": "12"}}', content_type="application/json")
        self.assertEqual(response.data, "SUCCESS")
        self.assertEqual(response.status_code, 201)

    def test_fast_commit_post_invalid_package_revision(self):
        response = self.client_stub.post('/api/fastcommit/images',
                                         data='{"package_revision": [{"package": "ERICtest_CXP1234567", '
                                              '"version": "1"}], '
                                              '"image_version": {"image": {"name": "test"}, '
                                              '"version": "12"}}', content_type="application/json")
        self.assertEqual(response.data, "Failed to store data")
        self.assertEqual(response.status_code, 400)

    def test_fast_commit_post_failure(self):
        response = self.client_stub.post('/api/fastcommit/images',
                                         {"": ""})
        self.assertEqual(response.data, "Parsing error with JSON params")
        self.assertEqual(response.status_code, 400)

    def test_fast_commit_get(self):
        response = self.client_stub.get('/api/fastcommit/images')
        self.assertEqual(response.status_code, 200)

    def test_fast_commit_get_by_image_version_success(self):
        response = self.client_stub.get('/api/fastcommit/images/contents?image_name=test_image&image_version=1234')
        self.assertEqual(response.status_code, 200)

    def test_fast_commit_get_by_image_version_failure(self):
        response = self.client_stub.get('/api/fastcommit/images/contents?image_name=test_image&image_version=1')
        self.assertEqual(response.status_code, 400)
