"""Disable iprestriction completely."""

from iprestrict.models import RangeBasedIPGroup, IPRange, Rule


def load_data(**kwargs):
    allow_all()


def allow_all():
    all_group = get_or_create_all_group()

    Rule.objects.all().delete()
    Rule.objects.create(
        ip_group=all_group,
        action='A',
        url_pattern='ALL',
        rank=65536)


def get_or_create_all_group():
    all_group, created = RangeBasedIPGroup.objects.get_or_create(
        name='ALL', description='Matches ALL IP Addresses')
    if created:
        IPRange.objects.create(
            ip_group=all_group,
            first_ip='0.0.0.0',
            last_ip='255.255.255.255')
        IPRange.objects.create(
            ip_group=all_group,
            first_ip='0:0:0:0:0:0:0:0',
            last_ip='ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')
    return all_group
