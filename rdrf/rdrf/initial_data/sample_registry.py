'''
Sample registry.
'''
from ..models import Registry


deps = ['base', 'groups', 'users']


def load_data(**kwargs):
    Registry.objects.get_or_create(code='sample', defaults=dict(
        splash_screen='<h1>Sample Registry</h2>',
        name='Sample Registry',
        desc='Sample Registry',
    ))
