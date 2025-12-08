from django.contrib.auth.mixins import UserPassesTestMixin


class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin to allow access only to superusers/admins.
    """

    def test_func(self):
        return self.request.user.is_superuser


class AdminOrSelfMixin(UserPassesTestMixin):
    """
    Mixin to allow access to superusers OR the user themselves (for update/detail).
    Assumes the view has a `get_object()` method or similar that returns
    the target user.
    """

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True

        # Check if the target object is the user themselves
        # This requires the view to treat the object as the User instance
        target_user = self.get_object()
        return user == target_user
