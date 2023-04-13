from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TagViewSet, CustomUserViewSet, RecipeViewSet, \
    IngredientViewSet, UserSubscriptionViewSet, UserSubscriptionListViewSet,FavoriteRecipeViewSet, ShoppingCartViewSet

app_name = 'api'
router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'tags', TagViewSet)
router.register(r'recipes', RecipeViewSet)
router.register(r'ingredients', IngredientViewSet)

urlpatterns = [
    path('users/subscriptions/',
         UserSubscriptionListViewSet.as_view({'get':'list'})),
    path('users/<int:author_id>/subscribe/', UserSubscriptionViewSet.as_view(
        {'post': 'create', 'delete': 'destroy'}), name='user-subscribe'),
    path('recipes/<int:recipe_id>/favorite/', FavoriteRecipeViewSet.as_view({'post': 'create', 'delete':'destroy'})),
    path('recipes/<int:recipe_id>/shopping_cart/', ShoppingCartViewSet.as_view({'post': 'create', 'delete':'destroy'})),
    path('recipes/download_shopping_cart/',ShoppingCartViewSet.as_view({'get':'list'})),
    path('', include(router.urls)),
]
