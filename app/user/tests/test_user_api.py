from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_valid_user_success(self):
        payload = {
            'email': 'test@test.com',
            'password': 'testpass',
            'name': "test name"
        }
        res = self.client.post(CREATE_USER_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        user = get_user_model().objects.get(**res.data)
        assert user.check_password(payload['password'])
        assert 'testpass' not in res.data

    def test_user_exists(self):
        payload = {
            'email': 'test@test.com',
            'password': 'testpass'
        }
        create_user(**payload)

        res = self.client.post(CREATE_USER_URL, payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_too_short(self):
        payload = {
            'email': 'test@test.com',
            'password': 'pw'
        }
        res = self.client.post(CREATE_USER_URL, payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        assert not user_exists

    def test_create_token_for_user(self):
        payload = {'email': "test@test.com", 'password': 'testpassword'}
        create_user(**payload)
        res = self.client.post(TOKEN_URL, payload)
        assert 'token' in res.data
        assert res.status_code == status.HTTP_200_OK

    def test_create_token_invalid_credentials(self):
        create_user(email='test@test.com', password='testpassword')
        payload = {'email': 'test@test.com', 'password': 'wrong'}
        res = self.client.post(TOKEN_URL, payload)
        assert 'token' not in res.data
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_token_no_user(self):
        payload = {'email': 'test@test.com', 'password': 'testpass'}
        res = self.client.post(TOKEN_URL, payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert 'token' not in res.data

    def test_create_token_missing_field(self):
        res = self.client.post(TOKEN_URL, {'email': 'one', 'password': ''})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert 'token' not in res.data

    def test_retrieve_user_unauthorized(self):
        res = self.client.get(ME_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class PrivateUserAPITests(TestCase):

    def setUp(self):
        self.user = create_user(
            email='test@test.com',
            password='testpass',
            name='name'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        res = self.client.get(ME_URL)
        assert res.status_code == status.HTTP_200_OK
        assert res.data == {
            'name': self.user.name,
            'email': self.user.email
        }

    def test_post_not_allowed(self):
        res = self.client.post(ME_URL, {})
        assert res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_upate_user_profile(self):
        payload = {
            'name': 'new name',
            'password': 'newpass1234'
        }
        res = self.client.patch(ME_URL, payload)
        self.user.refresh_from_db()
        assert self.user.name == payload['name']
        assert self.user.check_password(payload['password'])
        assert res.status_code == status.HTTP_200_OK
