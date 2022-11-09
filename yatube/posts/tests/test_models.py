from django.test import TestCase


from ..models import Post, Group, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
        )

    def test_models_have_correct_object_names(self):
        post = PostModelTest.post
        exp_post_name = post.text[:15]
        self.assertEqual(exp_post_name, str(post))

        group = PostModelTest.group
        exp_group = group.title
        self.assertEqual(exp_group, str(group))

    def test_post_model_verbose(self):
        fields = {
            'text': 'Текст поста',
            'pub_date': 'Дата публикации',
            'author': 'Автор',
            'group': 'Группа',
        }
        for field, expected in fields.items():
            with self.subTest(value=field):
                self.assertEqual(
                    Post._meta.get_field(field).verbose_name,
                    expected
                )

    def test_post_model_help_text(self):
        field_help_texts = {
            'text': 'Введите текст поста',
            'group': 'Выберите группу',
        }
        for field, expected in field_help_texts.items():
            with self.subTest(value=field):
                self.assertEqual(
                    Post._meta.get_field(field).help_text,
                    expected
                )
