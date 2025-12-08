from typing import Any, Dict

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

User = get_user_model()


class UserService:
    @staticmethod
    def get_all_users() -> QuerySet:
        """
        Returns all users in the system.
        """
        return User.objects.all().order_by("-date_joined")

    @staticmethod
    def create_user(data: Dict[str, Any]) -> User:
        """
        Creates a new user.
        Passes data to the UserManager's create_user method.
        """
        # Extract password to handle it specifically if needed,
        # but UserManager.create_user handles it.
        password = data.pop("password", None)
        if not password:
            raise ValueError("Password is required to create a user.")

        return User.objects.create_user(password=password, **data)

    @staticmethod
    def update_user(user: User, data: Dict[str, Any]) -> User:
        """
        Updates an existing user.
        """
        for field, value in data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        user.save()
        return user

    @staticmethod
    def delete_user(user: User) -> None:
        """
        Deletes a user.
        Using standard delete (hard delete) as per standard auth behavior.
        """
        user.delete()
