'''
Sample registry.
'''
from rdrf.models.definition.models import Registry
from registry.groups.models import CustomUser, WorkingGroup


deps = ['base', 'groups', 'users']


def load_data(**kwargs):
    registry, _ = Registry.objects.get_or_create(code='sample', defaults=dict(
        splash_screen='<h1>Sample Registry</h2>',
        name='Sample Registry',
        desc='Sample Registry',
    ))
    wg1, _ = WorkingGroup.objects.get_or_create(
        name='Sample Registry Working Group 1', registry=registry)

    for username in ('admin', 'clinical', 'curator', 'genetic'):
        user = CustomUser.objects.get(username=username)
        user.registry.add(registry)
        user.working_groups.add(wg1)
        user.save()
