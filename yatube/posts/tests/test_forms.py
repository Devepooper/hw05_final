from http import HTTPStatus
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Post, Group, User, Comment
from django.contrib.auth import get_user_model
from django.urls import reverse
import shutil
import tempfile
from django.conf import settings


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    """Создаем тестовые посты, группу и форму."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='leo')
        cls.group = Group.objects.create(
            title='Группа поклонников графа',
            slug='tolstoi',
            description='Что-то о группе'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='пост',
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        """Удаляем тестовые медиа."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUp(self):
        """Создаем клиент зарегистрированного пользователя."""
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)
        self.guest_client = Client()

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый пост',
            'group': PostFormTests.group.pk,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        post = Post.objects.first()
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': PostFormTests.user.username}
        ))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(
            post.group, PostFormTests.group
        )
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, PostFormTests.user)
        self.assertEqual(post.image, 'posts/small.gif')

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post = Post.objects.create(
            author=self.user,
            text="Тестовый текст",
        )
        group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        posts_count = Post.objects.count()
        form_data = {
            "text": "Изменяем текст",
            "group": group.id,
            "image": uploaded,
        }
        response = self.authorized_client.post(
            reverse("posts:post_edit", args=({post.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse("posts:post_detail", kwargs={"post_id": post.id})
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter(text="Изменяем текст").exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_client_create_post_form(self):
        """Анон не создаст запись в Post."""
        post_count = Post.objects.count()
        response = self.client.get(reverse('posts:post_create'))
        self.assertRedirects(
            response, '/auth/login/?next=/create/')
        self.assertEqual(Post.objects.count(), post_count)

    def test_create_comment(self):
        """Валидная форма создает запись в Comment."""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Новый коммент'
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostFormTests.post.pk}
            ),
            data=form_data,
            follow=True
        )
        comment = Comment.objects.first()
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': PostFormTests.post.pk}
        ))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.post, PostFormTests.post)
        self.assertEqual(comment.author, PostFormTests.user)

    def test_guest_client_cannot_create_comment_for_post(self):
        """"Анон не создаст коммент"""
        Post.objects.create(
            text='Тестовый текст',
            author=self.user
        )
        form_data = {
            'text': 'Тестовый комментарий',
            'author': self.guest_client,
        }
        post_id = Post.objects.count()
        comments_count = Comment.objects.count()
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post_id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
