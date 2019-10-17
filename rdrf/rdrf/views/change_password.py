from django.contrib.auth.views import PasswordChangeView
from django.conf import settings


class ChangePasswordView(PasswordChangeView):

    def get(self, request):
        # Check change password is enabled
        if not settings.ENABLE_PWD_CHANGE:
            raise Exception("Access forbidden - can not change password")

        return super().get(request)

    def post(self, request):
        # Check change password is enabled
        if not settings.ENABLE_PWD_CHANGE:
            raise Exception("Access forbidden - can not change password")

        return super().post(request)
