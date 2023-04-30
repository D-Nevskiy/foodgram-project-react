from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Ingredient, Recipe, RecipeIngredient, Tag


@admin.register(Ingredient)
class IngredientAdmin(ImportExportModelAdmin):
    pass


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [RecipeIngredientInline]


admin.site.register(Tag)
