from typing import Optional, List
from datetime import datetime
from dateutil.relativedelta import relativedelta
from rdrf.helpers.utils import parse_iso_datetime

# Schedule config in metadata ( The absolute time t in months after baseline.)
# A list of dictionaries like:
# infinite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}, {"t": "thereafter","form": "blah"}]
# finite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}]
# Because these are all expressed in month deltas, better to use python-dateutil to manipulate the dates


class NoBaseline(Exception):
    pass


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


class Schedule:
    def __init__(self, config, patient):
        self.items = config["items"]
        self.baseline_form_name = config["baseline_form_name"]
        self.patient = patient

    @property
    def intervals(self):
        # e.g. [6,12,24]
        return sorted([item["t"] for item in self.items if item["t"] != "thereafter"])

    @property
    def is_infinite(self):
        for item in self.items:
            if "thereafter" in item:
                return True

    def schedule_from_baseline(self, baseline_date: datetime):
        """
        For a given baseline, return a list of triples showing the expected date
        and form needed ( the finite part.), emit the t value for checking later
        as the third item
        """
        schedule = []
        for item in self.items:
            k = item["t"]
            if k != "thereafter":
                t = int(item["t"])
                d = baseline_date + relativedelta(months=t)
                form = item["form"]
                schedule.append((d, form, k))
        return sorted(schedule, key=lambda pair: pair[0])

    def get_summary(self):
        baseline = self.patient.baseline  # baseline clinical data record
        baseline_date = self._get_collection_date(baseline, self.baseline_form_name)
        schedule = self.schedule_from_baseline(baseline_date)
        responses = self.get_responses(schedule)

        summary = {}
        for r in responses:
            seq = r.seq
            if seq not in summary:
                summary[seq] = [r]
            else:
                summary[seq].append(r)

        return summary

    def get_responses(self, schedule) -> List[Response]:
        responses = []
        followups = self.patient.follow_ups  # these are clinicaldata records

        for followup in followups:
            try:
                form_dicts = followup.data["forms"]
                form_names = [d["name"] for d in form_dicts]
                assert len(form_names) == 1, "Should only be one form in each followup"
                form_name = form_names[0]
                coll_date = self._get_collection_date(followup, form_name)
                responses.append(Response(schedule, coll_date, form_name, followup))
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
