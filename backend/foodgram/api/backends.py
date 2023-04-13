from users.models import User, Subscription
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Для изменения бэкенд-авторизации"""
    @staticmethod
    def authenticate(request, email=None, password=None, **kwargs):
        UserModel = User
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_password(password):
                return user
        return None