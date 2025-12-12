from apps.nutrition.models.ingredient import FeedIngredient


class IngredientService:
    @staticmethod
    def get_deleted_ingredients():
        return FeedIngredient.all_objects.filter(is_deleted=True).order_by(
            "-modified_at"
        )

    @staticmethod
    def restore_ingredient(pk):
        ingredient = FeedIngredient.all_objects.get(pk=pk)
        ingredient.restore()
        return ingredient

    @staticmethod
    def hard_delete_ingredient(pk):
        ingredient = FeedIngredient.all_objects.get(pk=pk)
        ingredient.delete(destroy=True)
