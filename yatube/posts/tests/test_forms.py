import shutil
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.db.models import Max

from ..models import Group, Post, User


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост для тестирования',
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def last_post_test(self, post_id, text, author, group):
        last_post = Post.objects.first()
        self.assertEqual(last_post.id, post_id)
        self.assertEqual(last_post.text, text)
        self.assertEqual(last_post.group, group)
        self.assertEqual(last_post.author, author)

    def test_guest_client_post_create(self):
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Пост от неавторизованного клиента',
            'group': self.group.id,
            'image': uploaded
        }
        self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertFalse(Post.objects.filter(
            text='Пост от неавторизованного клиента').exists())

    def test_create_post(self):
        data = {
            'text': 'Новый пост',
            'group': self.group.pk,

        }
        post_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.author.username}))
        new_post_id = Post.objects.aggregate(Max("id")).get('id__max')
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.last_post_test(
            new_post_id,
            'Новый пост',
            self.author,
            self.group
        )

    def test_edit_existing_post(self):
        data = {
            'text': 'Изменённый пост',
            'group': self.group.pk
        }
        post_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.assertEqual(Post.objects.count(), post_count)
        self.last_post_test(
            self.post.id,
            'Изменённый пост',
            self.author,
            self.group,
        )
