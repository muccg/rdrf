import logging
from rdrf.models.definition.models import DropdownLookup

logger = logging.getLogger(__name__)


class DataSource(object):

    def __init__(self, context, tag):
        self.context = context
        self.tag = tag

    def values(self):
        return []


class ModelDataSource(DataSource):

    def values(self):
        items = []
        dropdown_lookup_objects = DropdownLookup.objects.filter(tag=self.tag)
        for object in dropdown_lookup_objects:
            items.append((object.value, object.label))
        return items
