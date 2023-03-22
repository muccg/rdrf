from typing import Optional, List
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from rdrf.helpers.utils import parse_iso_datetime

import logging

logger = logging.getLogger(__name__)

from dataclasses import dataclass

# Schedule config in metadata ( The absolute time t in months after baseline.)
# A list of dictionaries like:
# infinite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}, {"t": "thereafter","form": "blah"}]
# finite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}]
# Because these are all expressed in month deltas, better to use python-dateutil to manipulate the dates


COLLECTION_DATE = "COLLECTIONDATE"


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

    def get_schedule_from_baseline(self, baseline_date: datetime) -> List[ScheduleItem]:
        schedule_items = []
        for item in self.items:
            k = item["t"]
            if k != "thereafter":
                t = int(item["t"])
                d = baseline_date + relativedelta(months=t)
                form = item["form"]
                si = ScheduleItem(form_name=form, proj_date=d)
                schedule_items.append(si)

        return sorted(schedule_items, key=lambda si: si.proj_date)

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


class PromsAction:
    def __init__(self, registry, patient, form, action_name):
        self.registry = registry
        self.patient = patient
        self.form = form
        self.action_name = action_name


class PromsDataAnalyser:
    """
    This class checks the state of the proms data
    for a given patient. From the provided schedule
    for the registry and the patient we can determine
    what actions are required to be performed
    """

    def __init__(self, registry, patient):
        self.registry = registry
        self.patient = patient
        self.baseline_form = registry.metadata["schedule"]["baseline_form"]
        # if a request has been sent out in this window of days before
        # present we dont resend
        self.send_window = registry.metadata["schedule"]["send_window"]
        self.actions = []

    def analyse(self):
        logger.debug("analysing patient {self.patient} for proms")
        self.check_baseline()
        self.check_followups()
        return self.actions

    def check_baseline(self):
        """
        checks whether a baseline proms request needs to be sent out
        """
        # has a baseline form being saved?
        # The issue here is that sometimes
        # users can save the baseline / followup forms
        # directly without ever creating a proms request
        # so we check for some data first
        logger.debug(f"checking baseline for {self.patient}")
        baseline = self.patient.baseline
        collection_date: Optional[datetime] = self.get_collection_date(
            baseline, self.baseline_form
        )
        logger.debug(f"baseline collection date = {collection_date}")
        if collection_date is None:
            # maybe a survey request was sent out recently
            cutoff = datetime.now() - timedelta(days=self.send_window)
            recent_requests = self.get_survey_requests(self.baseline_form, cutoff)
            if recent_requests.count() == 0:
                logger.debug(
                    f"There have been no recent surver requests for {self.baseline_form}"
                )
                action = PromsAction(
                    self.registry,
                    self.patient,
                    self.baseline_form,
                    "send_proms_request",
                )
                self.actions.append(action)
                logger.debug(f"added action {action.action_name}")
            else:
                logger.debug(
                    f"There are recent proms requests in last {self.send_window} days - won't send"
                )
        else:
            logger.debug(
                f"patient has already filled in the {self.baseline_form} with collection date = {collection_date} - won't send"
            )

    def get_survey_requests(self, form_name, cutoff: datetime):
        # assumes the required survey as a form model linked
        # all cic surveys have this
        from rdrf.models.definition.models import RegistryForm
        from rdrf.models.proms.models import Survey
        from rdrf.models.proms.models import SurveyRequest
        from rdrf.models.proms.models import SurveyRequestStates

        form_model = RegistryForm.objects.get(registry=self.registry, name=form_name)

        survey = Survey.objects.get(registry=self.registry, form=form_model)
        return SurveyRequest.objects.filter(
            registry=self.registry,
            survey_name=survey.name,
            state=SurveyRequestStates.REQUESTED,
            created__gte=cutoff,
        )

    def get_collection_date(self, cd, form_name) -> Optional[datetime]:
        # patient created but no forms saved at all
        if not cd:
            return None
        if not cd.data:
            return None
        if "forms" not in cd.data:
            return None

        for form_dict in cd.data["forms"]:
            if form_dict["name"] == form_name:
                for section_dict in form_dict["sections"]:
                    if not section_dict["allow_multiple"]:
                        for cde_dict in section_dict["cdes"]:
                            if cde_dict["code"] == COLLECTION_DATE:
                                value = cde_dict["value"]
                                if not value:
                                    return None
                                else:
                                    try:
                                        return parse_iso_datetime(value)
                                    except:
                                        return None

    def check_followups(self):
        logger.debug("check followups is todo")
