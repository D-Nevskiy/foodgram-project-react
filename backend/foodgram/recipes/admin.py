from django.contrib import admin
from .models import Recipe, Tag,Ingredient, RecipeIngredient
from import_export.admin import ImportExportModelAdmin


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
