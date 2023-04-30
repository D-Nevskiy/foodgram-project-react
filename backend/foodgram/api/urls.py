from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CustomUserViewSet, FavoriteRecipeViewSet,
                    IngredientViewSet, RecipeViewSet, ShoppingCartViewSet,
                    TagViewSet, UserSubscriptionViewSet)

app_name = 'api'
router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'tags', TagViewSet)
router.register(r'recipes', RecipeViewSet)
router.register(r'ingredients', IngredientViewSet)

urlpatterns = [
    path('users/subscriptions/',
         UserSubscriptionViewSet.as_view({'get': 'subscriptions'})),
    path('users/<int:author_id>/subscribe/', UserSubscriptionViewSet.as_view(
        {'post': 'subscribe', 'delete': 'subscribe'}), name='user-subscribe'),
    path('recipes/<int:recipe_id>/favorite/', FavoriteRecipeViewSet.as_view(
        {'post': 'favorite', 'delete': 'favorite'})),
    path('recipes/<int:recipe_id>/shopping_cart/', ShoppingCartViewSet.as_view(
        {'post': 'shopping_cart', 'delete': 'shopping_cart'})),
    path('recipes/download_shopping_cart/',
         ShoppingCartViewSet.as_view({'get': 'list'})),
    path('', include(router.urls)),
]
