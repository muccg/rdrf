# Provide a lookup for group names of the form rdrf.registry.groups.GROUPS.GENETIC_STAFF
# The tuple values are used to match against group names in the db (explicitly case insensitive or using .lower())
# GROUPS.SUPER_USER is a sentinel used to trigger membership to all groups for superuser
from collections import namedtuple
GroupLookup = namedtuple('GroupLookup',
                         ['PATIENT',
                          'PARENT',
                          'CLINICAL',
                          'GENETIC_STAFF',
                          'GENETIC_CURATOR',
                          'WORKING_GROUP_STAFF',
                          'WORKING_GROUP_CURATOR',
                          'SUPER_USER',
                          'CARRIER'])
GROUPS = GroupLookup('patients',
                     'parents',
                     'clinical staff',
                     'genetic staff',
                     'genetic curator',
                     'working group staff',
                     'working group curators',
                     '__super_user__',
                     'carriers')
