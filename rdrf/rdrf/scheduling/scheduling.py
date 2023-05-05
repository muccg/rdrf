from typing import Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from rdrf.helpers.utils import parse_iso_datetime
from rdrf.helpers.utils import has_consented_to_receive_proms_emails
from dataclasses import dataclass

import logging

logger = logging.getLogger(__name__)


COLLECTION_DATE = "COLLECTIONDATE"


def get_responses(patient, registry):
    baseline = patient.baseline
    if baseline.data and "forms" in baseline.data:
        pass


@dataclass
class ScheduleItem:
    form_name: str
    proj_date: datetime  # projected collection date
    coll_date: Optional[datetime] = None  # actual collection date
    received: bool = False


class Scheduler:
    def __init__(self, config, baseline_collection_date):
        self.config = config
        # Schedule config in metadata ( The absolute time t in months after baseline.)
        # A list of dictionaries like:
        # infinite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}, {"t": "thereafter","form": "blah"}]
        # finite : [ {"t": 6, "form": "6MonthFollowUp"}, {"t": 12, "form": "12MonthFollowUp"}]
        # Because these are all expressed in month deltas, better to use python-dateutil to manipulate the dates
        self.items = config["items"]
        self.baseline_collection_date = baseline_collection_date

    @property
    def intervals(self):
        # e.g. [6,12,24]
        return sorted([item["t"] for item in self.items if item["t"] != "thereafter"])

    @property
    def is_infinite(self):
        for item in self.items:
            if "thereafter" in item:
                return True

    def get_followups_due(self, check_time: datetime):
        # todo followups after fixed intervals
        schedule_items = []
        for item in self.items:
            k = item["t"]
            if k != "thereafter":
                t = int(item["t"])
                proj_date = self.baseline_collection_date + relativedelta(months=t)
                if self.is_near(proj_date, check_time):
                    form = item["form"]
                    schedule_items.append((proj_date, form))

        return sorted(schedule_items, key=lambda pair: pair[0])

    def is_near(self, projected_date: datetime, check_time: datetime):
        days = abs((projected_date - check_time).days)
        return days <= self.config["window"]


class PromsAction:
    def __init__(self, registry, patient, form, action_name):
        self.registry = registry
        self.patient = patient
        self.form = form
        self.action_name = action_name


class AutomationException(Exception):
    pass


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
        self.config = registry.metadata.get("schedule", None)

        if self.config is None:
            raise AutomationException(
                f"Registry {self.registry.code} has no schedule in metadata"
            )

        self.send_window = self.config.get("send_window", 14)
        self.actions = []
        self.consent_followup = has_consented_to_receive_proms_emails(patient)
        self.check_time = datetime.now()
        self.baseline_collection_date = None

    def analyse(self):
        logger.debug("analysing patient {self.patient} for proms")
        self.check_baseline()
        if self.consent_followup:
            self.check_followups()
        else:
            logger.info(
                f"patient {self.patient.id} has not consented to receive followups"
            )
            logger.info("no followup checks will be performed.")
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
        self.baseline_collection_date: Optional[datetime] = self.get_collection_date(
            baseline, self.baseline_form
        )
        logger.debug(f"baseline collection date = {self.baseline_collection_date}")
        if self.baseline_collection_date is None:
            # maybe a survey request was sent out recently
            cutoff = self.check_time - timedelta(days=self.send_window)
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
                f"patient has already filled in the {self.baseline_form} with collection date = {self.baseline_collection_date} - won't send"
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
                                    except Exception:
                                        return None

    def check_followups(self):
        if self.baseline_collection_date is None:
            logger.info(
                f"No baseline collected for {self.patient.id} - followups can't automated"
            )
            return

        scheduler = Scheduler(self.config, self.baseline_collection_date)

        for due_date, form_name in scheduler.get_followups_due(self.check_time):
            if not self.followup_received(form_name, due_date):
                action = PromsAction(
                    self.registry, self.patient, form_name, "send_proms_request"
                )
                self.actions.append(action)
