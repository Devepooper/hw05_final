from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from posts.forms import PostForm
import shutil
import tempfile
from django.conf import settings
from django.core.cache import cache

from ..models import Post, Group, Follow


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        cls.user_author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тест ЗаголовОЧКА',
            slug='test-slug',
            description='Что-то о чем-то',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        """Удаляем тестовые медиа."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def check_post(self, response, is_post=False):
        cache.clear()
        if is_post:
            post = response.context.get('post')
        else:
            post = response.context['page_obj'][0]
        post_group = post.group
        post_text = post.text
        post_author = post.author
        post_data = post.pub_date
        post_image = post.image
        self.assertEqual(post_group, self.post.group)
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_author, self.post.author)
        self.assertEqual(post_data, self.post.pub_date)
        self.assertEqual(post_image, 'posts/small.gif')

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_post_post_edit_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client .get(
            reverse('posts:post_edit', kwargs={'post_id': '1'})
        )
        self.assertEqual(response.context.get('is_edit'), True)
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_index_pages_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse('posts:index')))
        self.check_post(response)

    def test_group_list_pages_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,))
        ))
        self.check_post(response)
        self.assertEqual(
            response.context.get('group'), self.group
        )

    def test_profile_pages_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse(
            'posts:profile', args=(self.user,)
        )))
        self.check_post(response)
        self.assertEqual(
            response.context.get('author'),
            self.user
        )

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse(
            'posts:post_detail',
            args=(self.post.id,)
        )))
        self.check_post(response, True)

    def test_group_no_post(self):
        """Проверка создания поста"""
        new_group = Group.objects.create(
            title='Тестзаголовок',
            slug='new_group_test',
            description='Жить-быть',
        )
        Post.objects.create(
            author=self.user,
            text='Новый тестовый пост',
            group=self.group,
        )
        response = self.authorized_client.get(reverse(
            'posts:group_list', args=(new_group.slug,)
        ))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_paginator_correct_context(self):
        """Шаблон index, group_list и profile
        сформированы с корректным Paginator."""
        first_page = 10
        second_page = 8
        paginator_objects = []
        for index in range(1, 18):
            new_post = Post(
                author=PostPagesTests.user,
                text='Тестовый пост ' + str(index),
                group=PostPagesTests.group
            )
            paginator_objects.append(new_post)
        Post.objects.bulk_create(paginator_objects)
        paginator_data = {
            'index': reverse('posts:index'),
            'group': reverse(
                'posts:group_list',
                kwargs={'slug': PostPagesTests.group.slug}
            ),
            'profile': reverse(
                'posts:profile',
                kwargs={'username': PostPagesTests.user.username}
            )
        }
        pages = (
            (1, first_page),
            (2, second_page),
        )
        for paginator_place, paginator_page in paginator_data.items():
            for page, count in pages:
                with self.subTest(paginator_place=paginator_place, page=page):
                    response = self.authorized_client.get(
                        paginator_page, {'page': page}
                    )
                    self.assertEqual(len(response.context['page_obj']), count)

    def test_y_cache_index_page(self):
        """Тестирование кэширования постов главной страницы."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.post.delete()
        new_response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, new_response.content)
        cache.clear()
        last_response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, last_response.content)

    def test_user_can_unfollow(self):
        """Авторизованный пользователь может отписываться."""
        response_unfollow = self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user_author.username})
        )
        self.assertRedirects(response_unfollow, reverse('posts:follow_index'))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_user_can_follow(self):
        """Авторизованный пользователь может подписываться."""
        response_follow = self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_author.username})
        )
        self.assertRedirects(response_follow, reverse('posts:follow_index'))
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_follower_get_following_posts(self):
        """Подписчик видит посты пользователя, на которого подписан"""
        Follow.objects.create(user=self.user, author=self.user_author)
        post = Post.objects.create(
            author=self.user_author,
            text='Testing follow_index',
            group=self.group
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(response.context['page_obj'][0], post)
        self.assertNotIn(self.post, response.context['page_obj'])
