from datetime import datetime
from dateutil.relativedelta import relativedelta


class SurveyResponse:
    def __init__(self):
        self.form = None
        self.collection_date: datetime = None
        self.completed = False
        self.actual_collection_date = None


# Schedule config in metadata ( The absolute time t in months after baseline.)
# A list of dictionaries like:
# infinite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}, {"t": "thereafter","form": "blah"}]
# finite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}]
# Because these are all expressed in month deltas, better to use python-dateutil to manipulate the dates


class Schedule:
    def __init__(self, config):
        self.items = config  # see schedule examples above

    @property
    def infinite(self):
        for item in self.items:
            if "thereafter" in item:
                return True

    def schedule_from_baseline(self, baseline_date: datetime):
        """
        For a given baseline, return a list of pairs showing the expected date
        and form needed ( the finite part.)
        """
        schedule = []
        for item in self.items:
            t = item["t"]
            if t != "thereafter":
                t = int(item["t"])
                d = baseline_date + relativedelta(months=t)
                form = item["form"]
                schedule.append((d, form))
        return sorted(schedule, key=lambda pair: pair[0])
