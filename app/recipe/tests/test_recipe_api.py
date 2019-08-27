from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer
import tempfile
import os
from PIL import Image

RECIPES_URL = reverse('recipe:recipe-list')


def sample_tag(user, name='Main course'):
    return Tag.objects.create(
        user=user,
        name=name
    )


def sample_ingredient(user, name='Cinnamon'):
    return Ingredient.objects.create(
        user=user,
        name=name
    )


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def sample_recipe(user, **params):
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(params)
    return Recipe.objects.create(
        user=user,
        **defaults
    )


class PublicRecipeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RECIPES_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class PrivateRecipeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'testpasss'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        assert res.status_code == status.HTTP_200_OK
        assert res.data == serializer.data

    def test_recipes_limited_to_user(self):
        user2 = get_user_model().objects.create_user(
            'another@test.com',
            '12345'
        )
        sample_recipe(user=user2)
        sample_recipe(user=self.user)
        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1
        assert res.data == serializer.data

    def test_view_recipe_detail(self):
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))
        url = detail_url(recipe.id)
        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        assert res.data == serializer.data

    def test_create_basic_recipe(self):
        payload = {
            'title': 'Chocolate cheescake',
            'time_minutes': 5,
            'price': 10.0
        }
        res = self.client.post(RECIPES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            assert payload[key] == getattr(recipe, key)

    def test_create_recipe_with_tags(self):
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Dessert')
        payload = {
            'title': 'Avocado lime cake',
            'tags': [tag1.id, tag2.id],
            'time_minutes': 60,
            'price': 20.0
        }
        res = self.client.post(RECIPES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        assert tags.count() == 2
        assert tag1 in tags
        assert tag2 in tags

    def test_create_recipe_with_ingredients(self):
        ingredient1 = sample_ingredient(user=self.user, name='Prawns')
        ingredient2 = sample_ingredient(user=self.user, name='Ginger')
        payload = {
            'title': "Prawns with carry",
            'ingredients': [ingredient1.id, ingredient2.id],
            'time_minutes': 10,
            'price': 20.7
        }
        res = self.client.post(RECIPES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        assert ingredients.count() == 2
        assert ingredient1 in ingredients
        assert ingredient2 in ingredients

    def test_partial_update_recipe_with_patch(self):
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Curry')
        payload = {
            'title': "Chicken pie",
            'tags': [new_tag.id]
        }
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        assert recipe.title == payload['title']
        tags = recipe.tags.all()
        assert len(tags) == 1
        assert new_tag in tags

    def test_full_update_recipe_with_put(self):
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        payload = {
            'title': 'Carbonara',
            'time_minutes': 4,
            'price': 9.00
        }
        url = detail_url(recipe.id)
        self.client.put(url, payload)
        recipe.refresh_from_db()
        assert recipe.title == payload['title']
        assert recipe.time_minutes == payload['time_minutes']
        assert recipe.price == payload['price']
        tags = recipe.tags.all()
        assert len(tags) == 0


class RecipeImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@user.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    @patch('uuid.uuid4')
    def test_upload_image_to_recipe(self, mock_uuid):
        url = image_upload_url(self.recipe.id)
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            img = Image.new('RGB', (10, 10))
            img.save(ntf, format='JPEG')
            ntf.seek(0)
            res = self.client.post(url, {'image': ntf}, format='multipart')
            self.recipe.refresh_from_db()
            assert res.status_code == status.HTTP_200_OK
            assert 'image' in res.data
            assert os.path.exists(self.recipe.image.path)
            url = detail_url(self.recipe.id)
            res = self.client.get(url)
            assert 'image' in res.data
            assert '/recipe/test-uuid.jpg'in res.data['image']

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {'image': 'notimage'}, format='multipart')
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_recipes_by_tags(self):
        """Test returning recipes with specific tags"""
        recipe1 = sample_recipe(user=self.user, title='Thai vegetable curry')
        recipe2 = sample_recipe(user=self.user, title='Aubergine with tahini')
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Vegetarian')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        recipe3 = sample_recipe(user=self.user, title='Fish and chips')

        res = self.client.get(
            RECIPES_URL,
            {'tags': '{},{}'.format(tag1.id, tag2.id)}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_recipes_by_ingredients(self):
        """Test returning recipes with specific ingredients"""
        recipe1 = sample_recipe(user=self.user, title='Posh beans on toast')
        recipe2 = sample_recipe(user=self.user, title='Chicken cacciatore')
        ingredient1 = sample_ingredient(user=self.user, name='Feta cheese')
        ingredient2 = sample_ingredient(user=self.user, name='Chicken')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)
        recipe3 = sample_recipe(user=self.user, title='Steak and mushrooms')

        res = self.client.get(
            RECIPES_URL,
            {'ingredients': '{},{}'.format(ingredient1.id, ingredient2.id)}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

