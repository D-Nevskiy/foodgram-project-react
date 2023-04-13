from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.pagination import PageNumberPagination
from users.models import User, Subscription
from recipes.models import Recipe, Tag, Ingredient, RecipeIngredient, \
    ShoppingCart, Favorite
from djoser.serializers import UserCreateSerializer, UserSerializer
from api.backends import EmailBackend


class UsersCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания пользователя."""
    password = serializers.CharField(style={"input_type": "password"},
                                     write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'id', 'username', 'first_name', 'last_name', 'password']


class UsersSerializer(UserSerializer):
    """Сериализатор работы с пользователями."""
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed']

    def get_is_subscribed(self, object):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(user=user,
                                           author=object.id).exists()


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Сериализатор для краткой информации о рецепте"""

    class Meta:
        model = Recipe
        fields = [
            'id', 'name', 'image', 'cooking_time']


class UserWithRecipes(serializers.ModelSerializer):
    """Сериализатор для работы с подписками."""
    recipes = RecipeMinifiedSerializer(many=True)

    class Meta:
        model = User
        fields = ['email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count']
        pagination_class = PageNumberPagination


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с тегами."""

    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'slug']


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с ингридиентами."""

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для подробного описания ингредиентов в рецепте."""
    name = serializers.CharField(
        source='ingredient.name', read_only=True)
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient.id', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class AddIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления ингридиентов в рецепт"""
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с рецептами."""
    author = UserSerializer(read_only=True)
    id = serializers.ReadOnlyField()
    tags = serializers.PrimaryKeyRelatedField(many=True,
                                              queryset=Tag.objects.all())

    ingredients = AddIngredientSerializer(many=True)
    image = serializers.ImageField(max_length=None, use_url=True,
                                   read_only=True)

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time']

    def create(self, validated_data):
        user = self.context.get('request').user
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(author=user,
                                       **validated_data)
        recipe.tags.set(tags)
        RecipeIngredient.objects.bulk_create(
            [RecipeIngredient(
                recipe=recipe,
                ingredient=Ingredient.objects.get(pk=ingredient['id']),
                amount=ingredient.get('amount')
            ) for ingredient in ingredients])

        return recipe

    def update(self, instance, validated_data):
        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time)
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        RecipeIngredient.objects.filter(
            recipe=instance,
            ingredient__in=instance.ingredients.all()).delete()
        instance.tags.set(tags)
        RecipeIngredient.objects.bulk_create(
            [RecipeIngredient(
                recipe=instance,
                ingredient=Ingredient.objects.get(pk=ingredient['id']),
                amount=ingredient.get('amount')
            ) for ingredient in ingredients])
        instance.save()
        return instance

    def to_representation(self, instance):
        context = {'request': self.context.get('request')}
        return GetRecipeSerializer(instance, context=context).data


class GetRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для подробной информации о рецепте."""
    tags = TagSerializer(many=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(read_only=True, many=True,
                                             source='recipe_ingredient')
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def get_is_favorited(self, object):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, recipe=object).exists()

    def get_is_in_shopping_cart(self, object):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=object).exists()


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с подписками."""
    author = UserWithRecipes(read_only=True)
    user = UserWithRecipes()

    class Meta:
        model = Subscription
        fields = ['user', 'author']


class CustomAuthTokenSerializer(serializers.Serializer):
    """Сериализатор для работы с токенами."""
    email = serializers.EmailField(label="Email")
    password = serializers.CharField(
        label="Password",
        style={"input_type": "password"},
        trim_whitespace=False,
        write_only=True,
    )

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = EmailBackend.authenticate(
                request=self.context.get("request"), email=email,
                password=password)

            if not user:
                msg = "Не удается войти в систему с этими учетными данными."
                raise serializers.ValidationError(msg, code="authorization")

        else:
            msg = "Must include 'email' and 'password'."
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с избранными рецептами."""

    class Meta:
        model = Favorite
        fields = ['user', 'recipe']


class ShoppingCartSerializer(FavoriteSerializer):
    """Сериализатор для работы со списком покупок."""

    class Meta(FavoriteSerializer.Meta):
        model = ShoppingCart
