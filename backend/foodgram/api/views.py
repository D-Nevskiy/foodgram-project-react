from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from djoser.views import UserViewSet
from users.models import User, Subscription
from recipes.models import Tag, Recipe, Ingredient, Favorite, ShoppingCart, \
    RecipeIngredient
from .serializers import CustomAuthTokenSerializer, TagSerializer, \
    RecipeSerializer, IngredientSerializer, UsersSerializer, UserWithRecipes, \
    SubscriptionSerializer, RecipeMinifiedSerializer, FavoriteSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from django.http import HttpResponse
from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.pdfgen import canvas
from .permissions import IsAuthorOrReadOnly
from rest_framework.permissions import IsAuthenticated


class CustomUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователями."""
    serializer_class = UsersSerializer
    lookup_field = 'id'

    def get_permissions(self):
        if self.action == 'retrieve' or self.action == 'list' or \
                self.action == 'create':
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]


class CustomObtainAuthToken(ObtainAuthToken):
    """Вьюсет для создания токена."""
    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response({"auth_token": token.key})


class LogoutView(APIView):
    """Вьюсет для удаления токена."""
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        token = Token.objects.get(user=request.user)
        token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для обработки запросов на получение ингредиентов."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для обработки запросов на получение тегов"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами."""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthorOrReadOnly]


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов создание и удаление подписки."""
    queryset = User.objects.all()
    serializer_class = UserWithRecipes
    lookup_field = 'id'
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        user = request.user
        author_id = self.kwargs.get('author_id')
        if not author_id:
            return Response(
                {'error': 'Требуется идентификатор автора.'},
                status=status.HTTP_400_BAD_REQUEST)

        author = User.objects.filter(id=author_id).first()
        if not author:
            return Response({'error': 'Автор не найден'},
                            status=status.HTTP_404_NOT_FOUND)

        if author == user:
            return Response({'error': 'Вы не можете подписаться на себя'},
                            status=status.HTTP_400_BAD_REQUEST)

        subscription_exists = Subscription.objects.filter\
            (user=user, author=author).exists()

        if subscription_exists:
            return Response({'error': 'Вы уже подписаны на этого автора.'},
                            status=status.HTTP_400_BAD_REQUEST)

        subscription = Subscription.objects.create(user=user, author=author)
        user.is_subscribed = True
        user.save()
        serializer = UserWithRecipes(subscription.author)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        author_id = self.kwargs.get('author_id')
        if not author_id:
            return Response(
                {'error': 'Требуется идентификатор автора.'},
                status=status.HTTP_400_BAD_REQUEST)

        author = User.objects.filter(id=author_id).first()
        if not author:
            return Response({'error': 'Автор не найден'},
                            status=status.HTTP_404_NOT_FOUND)

        subscription_exists = Subscription.objects.filter(
            user=user, author=author).exists()

        if not subscription_exists:
            return Response({'error': 'Вы не подписаны на этого автора.'},
                            status=status.HTTP_400_BAD_REQUEST)
        Subscription.objects.filter(user=user, author=author).delete()
        user.is_subscribed = False
        user.save()
        return Response({},
                        status=status.HTTP_204_NO_CONTENT)


class UserSubscriptionListViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов на просмотр подписок"""
    serializer_class = SubscriptionSerializer
    pagination_class = PageNumberPagination

    def list(self, request):
        user = request.user
        subscriptions = Subscription.objects.filter(user=user)
        authors = [subscription.author for subscription in subscriptions]
        page = self.paginate_queryset(authors)

        if page is not None:
            serializer = UserWithRecipes(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = UserWithRecipes(authors, many=True)
        return Response(serializer.data)


class FavoriteRecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов на добавления
    и удаления избранных рецептов"""
    serializer_class = FavoriteSerializer

    def get_queryset(self):
        return Recipe.objects.filter(favorites__user=self.request.user)

    def create(self, request, *args, **kwargs):
        recipe_id = self.kwargs.get('recipe_id')
        if not recipe_id:
            return Response({'error': 'Требуется идентификатор рецепта.'},
                            status=status.HTTP_400_BAD_REQUEST)

        recipe = get_object_or_404(Recipe, pk=recipe_id)
        user = request.user

        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response({'error': 'Рецепт уже добавлен в избранное.'},
                            status=status.HTTP_400_BAD_REQUEST)

        Favorite.objects.create(user=user, recipe=recipe)
        serializer = RecipeMinifiedSerializer(recipe)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        recipe_id = self.kwargs.get('recipe_id')
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        user = request.user

        if not Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response({'error': 'Рецепт не найден в избранном.'},
                            status=status.HTTP_400_BAD_REQUEST)

        Favorite.objects.filter(user=user, recipe=recipe).delete()
        return Response({},
                        status=status.HTTP_204_NO_CONTENT)


class ShoppingCartViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов на просмотр, добавление в список покупок.
    Обработка запроса на скачивание списка покупок"""

    def get_queryset(self):
        return ShoppingCart.objects.filter(user=self.request.user)

    def list(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = (
            "attachment; filename='shopping_cart.pdf'"
        )
        p = canvas.Canvas(response)
        arial = ttfonts.TTFont('Arial', '../../data/arial.ttf')
        pdfmetrics.registerFont(arial)
        p.setFont('Arial', 14)
        p.drawString(100, 750, "Список покупок")

        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user).values_list(
            'ingredient__name', 'amount', 'ingredient__measurement_unit')

        ingr_list = {}
        for name, amount, unit in ingredients:
            if name not in ingr_list:
                ingr_list[name] = {'amount': amount, 'unit': unit}
            else:
                ingr_list[name]['amount'] += amount
        height = 700

        p.drawString(100, 750, 'Список покупок')
        for i, (name, data) in enumerate(ingr_list.items(), start=1):
            p.drawString(
                80, height,
                f"{i}. {name} ({data['unit']}) - {data['amount']}")
            height -= 25
        p.showPage()
        p.save()
        return response

    def create(self, request, *args, **kwargs):
        user = self.request.user
        recipe_id = self.kwargs.get('recipe_id')

        if not recipe_id:
            return Response({'error': 'Требуется идентификатор рецепта.'},
                            status=status.HTTP_400_BAD_REQUEST)
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response({'error': 'Уже добавлен в список продуктов'},
                            status=status.HTTP_400_BAD_REQUEST)
        ShoppingCart.objects.create(user=user, recipe=recipe)
        serializer = RecipeMinifiedSerializer(recipe)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        recipe_id = self.kwargs.get('recipe_id')
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        user = request.user

        if not ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response({'error': 'Рецепта нет в списках покупки'},
                            status=status.HTTP_400_BAD_REQUEST)

        ShoppingCart.objects.filter(user=user, recipe=recipe).delete()
        return Response({},
                        status=status.HTTP_204_NO_CONTENT)
