from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from djoser.views import UserViewSet
from users.models import User, Subscription
from recipes.models import Tag, Recipe, Ingredient, Favorite, ShoppingCart, \
    RecipeIngredient
from .serializers import CustomAuthTokenSerializer, TagSerializer, \
    RecipeSerializer, IngredientSerializer, UsersSerializer, UserWithRecipes, \
    SubscriptionSerializer, ShoppingCartSerializer, FavoriteSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from django.http import HttpResponse
from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.pdfgen import canvas
from .permissions import IsAuthorOrReadOnly, \
    IsAuthenticatedOrReadOnlyListRetrieve
from rest_framework.permissions import IsAuthenticated


class CustomUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователями."""
    queryset = User.objects.all().order_by('id')
    serializer_class = UsersSerializer
    permission_classes = [IsAuthenticatedOrReadOnlyListRetrieve, ]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        subscriptions = set(
            Subscription.objects.filter(user_id=self.request.user).values_list(
                'author_id', flat=True))
        context['subscriptions'] = subscriptions
        return context


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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        subscriptions = set(
            Subscription.objects.filter(user_id=self.request.user).values_list(
                'author_id', flat=True))
        favorites = set(
            Favorite.objects.filter(user_id=self.request.user).values_list(
                'recipe_id', flat=True))
        shopping = set(
            ShoppingCart.objects.filter(user_id=self.request.user).values_list(
                'recipe_id', flat=True))
        context['subscriptions'] = subscriptions
        context['favorites'] = favorites
        context['shopping'] = shopping
        return context


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов создание и удаление подписки."""
    serializer_class = SubscriptionSerializer
    queryset = Subscription.objects.all()
    lookup_field = 'author_id'
    permission_classes = (IsAuthenticated,)

    @action(methods=['POST', 'DELETE'], detail=True)
    def subscribe(self, request, author_id):
        author = get_object_or_404(User, pk=author_id)
        user = request.user
        subscription = Subscription.objects.filter(user=user, author=author)
        serializer = SubscriptionSerializer(
            data={'author': author, 'subscription': subscription},
            context={'request': request})
        if serializer.is_valid():
            if request.method == 'POST':
                serializer.save()
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            elif request.method == 'DELETE':
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def subscriptions(self, request):
        user = request.user
        authors = User.objects.filter(following__user=user)
        page = self.paginate_queryset(authors)
        serializer = UserWithRecipes(
            page, many=True,
            context={'request': request})
        return self.get_paginated_response(serializer.data)


class FavoriteRecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов на добавления
    и удаления избранных рецептов"""
    serializer_class = FavoriteSerializer

    def get_queryset(self):
        return Recipe.objects.filter(favorites__user=self.request.user)

    @action(methods=['POST', 'DELETE'], detail=True)
    def favorite(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        user = request.user
        favorites = Favorite.objects.filter(user=user, recipe=recipe)
        serializer = FavoriteSerializer(
            data={'recipe': recipe, 'favorites': favorites},
            context={'request': request})
        if serializer.is_valid():
            if request.method == 'POST':
                serializer.save()
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            elif request.method == 'DELETE':
                favorites.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ShoppingCartViewSet(viewsets.ModelViewSet):
    """Вьюсет для обработки запросов на просмотр, добавление в список покупок.
    Обработка запроса на скачивание списка покупок"""
    serializer_class = ShoppingCartSerializer

    def get_queryset(self):
        return Recipe.objects.filter(user=self.request.user)

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

    @action(methods=['POST', 'DELETE'], detail=True)
    def shopping_cart(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        user = request.user
        shopping = ShoppingCart.objects.filter(user=user, recipe=recipe)
        serializer = ShoppingCartSerializer(
            data={'recipe': recipe, 'shopping': shopping},
            context={'request': request})
        if serializer.is_valid():
            if request.method == 'POST':
                serializer.save()
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            elif request.method == 'DELETE':
                shopping.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
