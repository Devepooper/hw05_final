from http import HTTPStatus

from urllib.parse import urljoin

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User

User = get_user_model()


class PostsURLTests(TestCase):
    """Тесты URL приложения Post."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            group=cls.group,
            author=cls.user,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def public_pages_are_available_to_anonymous(self):
        """анон может попасть на публичные урлы"""
        public_templates = [
            "/",
            f"/group/{self.group.slug}/",
            f"/profile/{self.user}/",
            f"/posts/{self.post.id}/",
        ]
        for adress in public_templates:
            with self.subTest(adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url_exists_at_desired_location(self):
        """Страница /posts/<post_id>/edit/ доступна автору."""
        response = self.authorized_client.get(f"/posts/{self.post.id}/edit/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_anonymous_on_auth_login(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.guest_client.get("/create/")
        self.assertRedirects(response, "/auth/login/?next=/create/")

    def test_post_edit_redirect_for_non_author(self):
        """Проверка недоступности редактирования поста для не-автора"""
        user_non_author = User.objects.create_user(
            username='test_user_non_author'
        )
        self.authorized_client.force_login(user_non_author)
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.pk}))

    def test_create_url_redirect_anonymous_on_admin_login(self):
        """Страницы /create/, /edit/, /comment/
        перенаправит анонимного пользователя
        на страницу логина.
        """
        url_names = (
            (reverse('posts:post_create'), urljoin(
                reverse('users:login'), '?next=/create/')),
            (reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
                urljoin(reverse('users:login'),
                        f'?next=/posts/{self.post.pk}/edit/')),
            (reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
                urljoin(reverse('users:login'),
                        f'?next=/posts/{self.post.pk}/comment/'))
        )
        for url, redirect in url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, redirect)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ): 'posts/profile.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.pk}
            ): 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
