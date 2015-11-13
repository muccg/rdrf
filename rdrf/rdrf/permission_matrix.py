from django.auth import Group


from groups.auth import CustomUser


class Matrix(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.group_perms = {}
        self.user_perms = {}

    def _load_users(self):
        for user in CustomUser.objects.all():
            self.user_perms[user.username] = []

    def load_form_permissions(self):
        for user in CustomUser.objects.all():
            for form in self.registry_model.forms:
                if user.can_view(form):
                    self.user_perms[user.username].append(("form", form.name, "view"))
                if user.can_edit(form):
                    self.user_perms[user.username].append(("form", form.name, "edit"))



    def load_group_permissions(self):
        for group in Group.objects.all():
            self.group_perms[group.name] = []
            for permission in self._get_permissions(group):
                pass