# -*- coding: utf-8 -*-
from rdrf.models.definition.models import ClinicalData
from rdrf.helpers.utils import TimeStripper, HistoryTimeStripper
from django.db import transaction
import django
django.setup()


def fix_cdes_modjgos():
    cdes_queryset = ClinicalData.objects.filter(collection='cdes')
    cdes_ts = TimeStripper(cdes_queryset)

    try:
        with transaction.atomic():
            cdes_ts.forward()
            print("Fix succeeded: fixed cdes ClinicalData objects OK")
            return True

    except Exception as ex:
        print("Fix failed: rolled back: %s" % ex)
        return False


def fix_history_cdes_modjgos():
    history_queryset = ClinicalData.objects.filter(collection='history')
    history_ts = HistoryTimeStripper(history_queryset)

    try:
        with transaction.atomic():
            history_ts.forward()
            print("Fix succeeded: fixed history ClinicalData objects OK")
            return True

    except Exception as ex:
        print("Fix failed: rolled back: %s" % ex)
        return False


def usage():
    print("Usage:  fix_modjgo_dates [cdes|history]")


if __name__ == '__main__':
    import sys
    try:
        collection_name = sys.argv[1]
    except BaseException:
        usage()
        sys.exit(1)

    if collection_name == 'cdes':
        result = fix_cdes_modjgos()
        if not result:
            sys.exit(1)
    elif collection_name == 'history':
        result = fix_history_cdes_modjgos()
        if not result:
            sys.exit(1)
    else:
        usage()
        sys.exit(1)
