from django.test import TestCase, Client
from django.core.cache import cache
from django.conf import settings
from http import HTTPStatus
import shutil
import tempfile

from ..models import Post, Group, User


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='usname')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_urls_uses_correct_template(self):
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
        }
        found = ('/create/', )
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
                response = self.guest_client.get(address)
                if address in found:
                    self.assertEqual(response.status_code, HTTPStatus.FOUND)
                    continue
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_create_auth(self):
        responses = {
            self.authorized_client.get('/create/'),
            self.authorized_client.get(f'/posts/{self.post.id}/edit/')}
        for response in responses:
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_404(self):
        response = self.authorized_client.get('/smth/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
