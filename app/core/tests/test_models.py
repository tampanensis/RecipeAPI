from django.contrib.auth import get_user_model
from django.test import TestCase
from core import models


def sample_user(email='test@test.com', password='testpass'):
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):
    def test_create_user_with_email_successful(self):
        email = "tampa@mail.com"
        password = 'tampa'

        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        assert user.email == email
        assert user.check_password(password)

    def test_new_user_email_normalized(self):
        email = "tampa@MAIL.COM"
        user = get_user_model().objects.create_user(
            email=email,
            password='aaf'
        )
        assert user.email == email.lower()

    def test_new_user_invalid_email(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(None, 'test1234')

    def test_create_new_superuser(self):
        user = get_user_model().objects.create_superuser(
            'test@test.com',
            'test1234'
        )
        assert user.is_superuser
        assert user.is_staff

    def test_tag_str(self):
        tag = models.Tag.objects.create(
            user=sample_user(),
            name='Vegan'
        )
        assert str(tag) == tag.name

    def test_ingredient_str(self):
        ingredient = models.Ingredient.objects.create(
            user=sample_user(),
            name='Cucumber'
        )

        assert str(ingredient) == ingredient.name
