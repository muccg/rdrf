'''
Sample registry.
'''
from rdrf.models.definition.models import Registry
from registry.groups.models import CustomUser, WorkingGroup


deps = ['base', 'groups', 'users']


def load_data(**kwargs):
    if not Registry.objects.all().count():
        registry, _ = Registry.objects.get_or_create(code='sample', defaults=dict(
            splash_screen='<h1>Sample Registry</h1>',
            name='Sample Registry',
            desc='Sample Registry',
        ))

    if not WorkingGroup.objects.all().count():
        registry = Registry.objects.get()
        wg1, _ = WorkingGroup.objects.get_or_create(
            name='Working Group', registry=registry)

        for username in ('admin', 'clinical', 'curator', 'genetic'):
            user = CustomUser.objects.get(username=username)
            user.registry.add(registry)
            user.working_groups.add(wg1)
            user.save()
