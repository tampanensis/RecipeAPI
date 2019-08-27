from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        res = self.client.get(INGREDIENTS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class PrivateIngredientsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredient_list(self):
        Ingredient.objects.create(
            user=self.user,
            name='Kale'
        )
        Ingredient.objects.create(
            user=self.user,
            name='Salt'
        )
        res = self.client.get(INGREDIENTS_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        assert res.status_code == status.HTTP_200_OK
        assert res.data == serializer.data

    def test_ingredients_limited_to_user(self):
        user2 = get_user_model().objects.create_user(
            'another@test.com',
            'testpass'
        )
        Ingredient.objects.create(
            user=user2,
            name='Vinegar'
        )
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Tumeric'
        )
        res = self.client.get(INGREDIENTS_URL)
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1
        assert res.data[0]['name'] == ingredient.name

    def test_create_ingredient_successful(self):
        payload = {
            'name': 'Cabbage'
        }
        self.client.post(INGREDIENTS_URL, payload)
        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name'],
        ).exists()
        assert exists

    def test_create_ingredient_invalid(self):
        payload = {
            'name': ''
        }
        res = self.client.post(INGREDIENTS_URL, payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_ingredients_assigned_to_recipes(self):
        ingredient1 = Ingredient.objects.create(
            user=self.user,
            name='Apple'
        )
        ingredient2 = Ingredient.objects.create(
            user=self.user,
            name='Banana'
        )
        recipe = Recipe.objects.create(
            title='Apple cake',
            time_minutes=5,
            price=10.0,
            user=self.user
        )
        recipe.ingredients.add(ingredient1)
        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)
        assert serializer1.data in res.data
        assert serializer2.data not in res.data

    def test_ingredient_assigned_unique(self):
        ingredient = Ingredient.objects.create(
            user=self.user, name='Eggs'
        )
        Ingredient.objects.create(
            user=self.user, name='Vanilla'
        )
        recipe1 = Recipe.objects.create(
            title='Fish and chips',
            time_minutes=30,
            price=20.0,
            user=self.user
        )
        recipe1.ingredients.add(ingredient)
        recipe2 = Recipe.objects.create(
            title='Coriander eggs',
            time_minutes=20,
            price=40.0,
            user=self.user
        )
        recipe2.ingredients.add(ingredient)
        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        assert len(res.data) == 1
