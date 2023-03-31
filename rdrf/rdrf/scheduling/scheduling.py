from typing import Optional, List
from datetime import datetime
from dateutil.relativedelta import relativedelta
from rdrf.helpers.utils import parse_iso_datetime
from dataclasses import dataclass

# Schedule config in metadata ( The absolute time t in months after baseline.)
# A list of dictionaries like:
# infinite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}, {"t": "thereafter","form": "blah"}]
# finite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}]
# Because these are all expressed in month deltas, better to use python-dateutil to manipulate the dates


class ResponseType:
    BASELINE = "baseline"
    FOLLOWUP = "followup"


def get_responses(patient, registry):
    baseline = patient.baseline
    if baseline.data and "forms" in baseline.data:
        pass


class NoBaseline(Exception):
    pass


class ScheduleAction:
    REMIND = "remind"  # system need to remind patient
    NOTIFY = "notify"  # system needs to notify
    BASELINE = "baseline"
    FOLLOWUP = "followup"


class Response:
    def __init__(self, schedule, coll_date, form_name, followup):
        self.schedule = schedule  # we need the schedule to determine the seq number
        self.coll_date = coll_date
        self.form_name = form_name
        self.followup = followup

    def near(self, date):
        days = abs(self.get_distance(date))
        return days <= 14

    def get_distance(self, coll_date):
        return (coll_date - self.coll_date).days

    @property
    def seq(self):
        proj_dates = [x[0] for x in self.schedule]
        dists = [self.get_distance(proj_date) for proj_date in proj_dates]
        min_dist = min(dists)
        min_dist_index = dists.index(min_dist)
        seq = min_dist_index + 1
        return seq


@dataclass
class ScheduleItem:
    form_name: str
    proj_date: datetime  # projected collection date
    coll_date: Optional[datetime] = None  # actual collection date
    received: bool = False

    def near(self, d: datetime):
        return abs((d - self.proj_date).days) <= 14


class Schedule:
    def __init__(self, registry, patient):
        self.registry = registry
        self.config = self.registry.metadata["schedule"]

        self.items = self.config["items"]
        self.baseline_form_name = self.config["baseline_form"]
        self.patient = patient
        self.baseline_date = self.get_baseline_date()
        self.schedule_items = self.get_schedule_from_baseline()
        if self.baseline_date:
            self.dates = [self.baseline_date] + [
                si.proj_date for si in self.schedule_items
            ]
        else:
            self.dates = []

    def __getitem__(self, index):
        if self.dates:
            return self.dates[index]
        else:
            return None

    def closest_seq(self, some_date):
        # for a given date , return the closest sequence number in
        # the schedule
        if not self.schedule_items:
            return None
        best_seq = None
        best_diff = 10000

        for index, proj_date in enumerate(self.dates):
            days_diff = abs(proj_date - some_date).days
            if days_diff < best_diff:
                best_seq = index
                best_diff = days_diff
        return best_seq

    @property
    def intervals(self):
        # e.g. [6,12,24]
        return sorted([item["t"] for item in self.items if item["t"] != "thereafter"])

    @property
    def is_infinite(self):
        for item in self.items:
            if "thereafter" in item:
                return True

    def get_schedule_from_baseline(self) -> List[ScheduleItem]:
        if self.baseline_date is None:
            return []

        schedule_items = []
        for item in self.items:
            k = item["t"]
            if k != "thereafter":
                t = int(item["t"])
                d = self.baseline_date + relativedelta(months=t)
                form = item["form"]
                si = ScheduleItem(form_name=form, proj_date=d)
                schedule_items.append(si)

        return sorted(schedule_items, key=lambda si: si.proj_date)

    def get_baseline_date(self):
        try:
            baseline = self.patient.baseline  # baseline clinical data record
            return self._get_collection_date(baseline, self.baseline_form_name)
        except NoBaseline:
            return None

    def check(self):
        # this is todo
        # just blocking out
        baseline = self.patient.baseline  # baseline clinical data record
        try:
            baseline_date = self._get_collection_date(baseline, self.baseline_form_name)
        except NoBaseline:
            return [ScheduleAction.BASELINE, self.patient.id]

        schedule_items = self.get_schedule_from_baseline(baseline_date)
        responses = self.get_responses()

        found = []

        for form_name, coll_date in responses:
            for schedule_item in schedule_items:
                if schedule_item.form_name == "form_name" and schedule_item.near(
                    coll_date
                ):
                    found.append((form_name, coll_date, schedule_item))

        return found

    def get_responses(self):
        responses = []
        followups = self.patient.follow_ups  # these are clinicaldata records

        for followup in followups:
            try:
                form_dicts = followup.data["forms"]
                form_names = [d["name"] for d in form_dicts]
                assert len(form_names) == 1, "Should only be one form in each followup"
                form_name = form_names[0]
                coll_date = self._get_collection_date(followup, form_name)
                responses.append((form_name, coll_date))
            except KeyError:
                pass
        return responses

    def _get_collection_date(self, cd, form_name) -> Optional[datetime]:
        """
        Assumes onely one collection date field in the form
        somewhere
        """
        if cd.data and "forms" in cd.data:
            for form_dict in cd.data["forms"]:
                if form_dict["name"] == form_name:
                    for section_dict in form_dict["sections"]:
                        if not section_dict["allow_multiple"]:
                            for cde_dict in section_dict["cdes"]:
                                if cde_dict["code"] == "COLLECTIONDATE":
                                    value = cde_dict["value"]
                                    coll_date = parse_iso_datetime(value)
                                    return coll_date
