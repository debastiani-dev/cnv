from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserForm(forms.ModelForm):
    """
    Form for Admins to Create/Update users.
    Includes password field for creation.
    """

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        required=False,
        help_text=_(
            "Required for new users. Leave empty to keep existing password when updating."
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
            "profile_image",
        ]

    def clean_password(self):
        password = self.cleaned_data.get("password")
        # For new users (not yet saved to database), password is required
        # Uses _state.adding instead of checking pk because UUID pks are auto-generated
        # pylint: disable=protected-access
        if self.instance._state.adding and not password:
            raise forms.ValidationError(_("Password is required for new users."))
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class UserUpdateSelfForm(forms.ModelForm):
    """
    Form for Users to update their OWN profile.
    Restricted fields.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "profile_image"]
