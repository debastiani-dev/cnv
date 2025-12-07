from django.contrib.auth import models as auth_models
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import BaseUserManager as CustomBaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseManager, BaseModel


class UserManager(BaseManager, CustomBaseUserManager):
    """
    Manager that combines the soft-delete logic (BaseManager)
    and the user management logic (CustomBaseUserManager).
    """

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        if hasattr(self.model, "is_staff"):
            extra_fields.setdefault("is_staff", False)
        if hasattr(self.model, "is_superuser"):
            extra_fields.setdefault("is_superuser", False)

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)


class User(BaseModel, AbstractBaseUser, auth_models.PermissionsMixin):
    """
    Concrete User model.
    Inherits from:
    - BaseModel (UUID, Soft Delete, created_at, modified_at)
    - AbstractBaseUser (Password, Last Login, Auth methods)
    - PermissionsMixin (Groups, Permissions, is_superuser)
    """

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[auth_models.AbstractUser.username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    email = models.EmailField(_("email address"), blank=True)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )

    # is_active is defined as True in AbstractBaseUser snippet,
    # but usually it's a field in Django.
    # The snippet had: is_active = True. This makes it a class attribute,
    # effectively always True?
    # Django's default AbstractUser has it as a BooleanField.
    # I should override it as a field to allow deactivation.
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )

    date_joined = models.DateTimeField(_("date joined"), auto_now_add=True)

    objects = UserManager()  # type: ignore[misc]

    EMAIL_FIELD = "email"  # type: ignore[misc]
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta(BaseModel.Meta):
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        # from django.core.mail import send_mail
        # send_mail(subject, message, from_email, [self.email], **kwargs)
