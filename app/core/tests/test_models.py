from django.contrib.auth import get_user_model
from django.test import TestCase


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

