from apps.nutrition.models.diet import Diet


class DietService:
    @staticmethod
    def get_deleted_diets():
        return Diet.all_objects.filter(is_deleted=True).order_by("-modified_at")

    @staticmethod
    def restore_diet(pk):
        diet = Diet.all_objects.get(pk=pk)
        diet.restore()
        return diet

    @staticmethod
    def hard_delete_diet(pk):
        diet = Diet.all_objects.get(pk=pk)
        diet.delete(destroy=True)
