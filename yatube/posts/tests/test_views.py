from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from django.conf import settings
import tempfile
import shutil
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..models import Post, Group, User, Follow


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='usname')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug'
        )
        cls.gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='gif',
            content=cls.gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='текст',
            group=cls.group,
            image=cls.uploaded
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

    def test_pages_uses_correct_template(self):
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': self.post.author.username}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(template=template):
                if template != f'/posts/{self.post.id}/edit/':
                    response = self.authorized_client.get(reverse_name)
                    self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.image, self.post.image)

    def test_group_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:group_list',
                                              kwargs={'slug':
                                                      self.group.slug}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.group, self.post.group)
        self.assertEqual(first_object.image, self.post.image)

    def test_profile_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:profile',
                                              kwargs={'username':
                                                      self.post.author.username
                                                      }))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.image, self.post.image)

    def test_detail_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_detail',
                                              kwargs={'post_id':
                                                      self.post.id}))
        first_object = response.context['post']
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author.posts.count(),
                         self.post.author.posts.count())
        self.assertEqual(first_object.image, self.post.image)

    def test_create_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_edit',
                                              kwargs={'post_id':
                                                      self.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
                self.assertEqual(response.context['is_edit'], True)

    def test_check_post_on_create(self):
        pages = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user}),
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(response.context.get('page_obj')[0],
                                 self.post, f'{self.post.id}')

    def test_cache(self):
        """Тест кэша."""
        post = Post.objects.create(
            text='text',
            author=self.user
        )
        response = self.authorized_client.get(reverse('posts:index'))
        response_post = response.context['page_obj'][0]
        self.assertEqual(post, response_post)
        post.delete()
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, response_3.content)


class PostPaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug='test-slug',
            description='Тестовое описание',
        )
        batch = [Post(author=cls.user,
                      text='Тестовый пост для тестирования',
                      group=cls.group) for i in range(13)]
        cls.post = Post.objects.bulk_create(batch, batch_size=13)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_posts(self):
        namespace_list = {
            'posts:index': reverse('posts:index'),
            'posts:group_list': reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}),
            'posts:profile': reverse(
                'posts:profile', kwargs={'username': self.user.username}),
        }
        count_posts = 10
        for template, reverse_name in namespace_list.items():
            response = self.guest_client.get(reverse_name)
            self.assertEqual(len(response.context['page_obj']), count_posts)

    def test_second_page_contains_ten_posts(self):
        namespace_list = {
            'posts:index': reverse('posts:index') + "?page=2",
            'posts:group_list': reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}) + "?page=2",
            'posts:profile': reverse(
                'posts:profile',
                kwargs={'username': self.user.username}) + "?page=2",
        }
        count_posts = 3
        for template, reverse_name in namespace_list.items():
            response = self.guest_client.get(reverse_name)
            self.assertEqual(len(response.context['page_obj']), count_posts)


class FollowTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscriber = User.objects.create_user(username='follower')
        cls.subscriber_2 = User.objects.create_user(
            username='subscriber_2')
        cls.author = User.objects.create_user(username='following')
        cls.follow = Follow.objects.create(
            user=cls.subscriber,
            author=cls.author,
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.subscriber)
        self.subscriber_2_client = Client()
        self.subscriber_2_client.force_login(self.subscriber_2)
        cache.clear()

    def test_follow(self):
        """Зарегистрированный пользователь может подписываться."""
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author})
        )
        self.assertTrue(Follow.objects.filter(
            user=self.subscriber,
            author=self.author,
        ).exists())

    def test_unfollow(self):
        """Зарегистрированный пользователь может отписаться."""
        self.authorized_client.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.author})
        )
        self.assertFalse(Follow.objects.filter(
            user=self.subscriber,
            author=self.author,
        ).exists())

    def test_follow_page_follower(self):
        """Проверка, что посты появляются по подписке."""
        response = self.authorized_client.get(reverse(
            'posts:follow_index'
        ))
        follower_posts_cnt = len(response.context['page_obj'])
        self.assertEqual(follower_posts_cnt, 1)
        post = Post.objects.get(id=self.post.pk)
        self.assertIn(post, response.context['page_obj'])

    def test_follow_page_unfollower(self):
        """Проверка, что посты не появляются если не подписан."""
        response = self.subscriber_2_client.get(reverse(
            'posts:follow_index'))
        posts_cnt_new = len(response.context['page_obj'].object_list)
        self.assertEqual(posts_cnt_new, 0)
