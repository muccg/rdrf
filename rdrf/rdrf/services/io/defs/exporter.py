import datetime
import json
import logging
import yaml
from decimal import Decimal
from django.forms.models import model_to_dict
from explorer.models import Query
from operator import attrgetter
from rdrf.models.definition.models import DemographicFields, RegistryForm
from rdrf.models.definition.models import Section, CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue

from rdrf import VERSION

logger = logging.getLogger(__name__)


class ExportException(Exception):
    pass


def convert_decimal_values(cde_dict):
    for k in cde_dict:
        value = cde_dict[k]
        if isinstance(value, Decimal):
            cde_dict[k] = str(value)
    return cde_dict


def cde_to_dict(cde):
    return convert_decimal_values(model_to_dict(cde))


class ExportFormat:
    JSON = "JSON"
    YAML = "YAML"


class ExportType:
    # Only registry, forms , sections - No CDEs
    REGISTRY_ONLY = "REGISTRY_ONLY"
    # As above with cdes used by the registry
    REGISTRY_PLUS_CDES = "REGISTRY_PLUS_CDES"
    REGISTRY_PLUS_ALL_CDES = "REGISTRY_PLUS_ALL_CDES"   # registry + all cdes in the site
    # only the cdes in the supplied registry ( no forms)
    REGISTRY_CDES = "REGISTRY_CDES"
    ALL_CDES = "ALL_CDES"                               # All CDEs in the site


class Exporter(object):

    """
    Export a registry definition to yaml or json
    """

    def __init__(self, registry_model):
        self.registry = registry_model

    def export_yaml(self, export_type=ExportType.REGISTRY_PLUS_CDES):
        """
        Example output:
        ----------------------------------------------------------------------
        code: FH
        desc: This is a description that might take a few lines.
        forms:
        - is_questionnaire: false
          name: Foobar
          display_name: foobar
          sections:
          - allow_multiple: false
            code: SEC001
            display_name: Physical Characteristics
            elements: [CDE01, CDE03, CDE05]
            extra: 0
          - allow_multiple: true
            code: SEC002
            display_name: Disease
            elements: [CDE88, CDE67]
            extra: 1
        - is_questionnaire: false
          name: Glug
          display_name: glug
          sections:
          - allow_multiple: false
            code: SEC89
            display_name: Test Section
            elements: [CDE99, CDE67]
            extra: 0
        name: FascioH.. Registry
        splash_screen: todo
        version: 1.0
        ----------------------------------------------------------------------


        :return: a yaml file containing the definition of a registry
        """
        try:
            export = self._export(ExportFormat.YAML, export_type)
            return export, []
        except Exception as ex:
            return None, [ex]

    def export_json(self):
        return self._export(ExportFormat.JSON)

    def _get_cdes(self, export_type):
        if export_type == ExportType.REGISTRY_ONLY:
            cdes = set([])
        elif export_type in [ExportType.REGISTRY_PLUS_CDES, ExportType.REGISTRY_CDES]:
            cdes = set([cde for cde in self._get_cdes_in_registry(self.registry)])
        elif export_type in [ExportType.ALL_CDES, ExportType.REGISTRY_PLUS_ALL_CDES]:
            cdes = set([cde for cde in CommonDataElement.objects.order_by("code")])
        else:
            raise ExportException("Unknown export type")

        generic_cdes = self._get_generic_cdes()

        return self._sort_codes(cdes.union(generic_cdes))

    @staticmethod
    def _sort_codes(items):
        return sorted(items, key=attrgetter("code"))

    def _get_pvgs_in_registry(self, registry):
        pvgs = set([])

        for cde in self._get_cdes_in_registry(registry):
            if cde.pv_group:
                pvgs.add(cde.pv_group)
        return pvgs

    def _get_pvgs(self, export_type):
        if export_type == ExportType.REGISTRY_ONLY:
            pvgs = set([])
        elif export_type in [ExportType.REGISTRY_PLUS_CDES, ExportType.REGISTRY_CDES]:
            pvgs = set([pvg for pvg in self._get_pvgs_in_registry(self.registry)])
        elif export_type in [ExportType.ALL_CDES, ExportType.REGISTRY_PLUS_ALL_CDES]:
            pvgs = set([pvg for pvg in CDEPermittedValueGroup.objects.order_by("code")])
        else:
            raise ExportException("Unknown export type")
        return self._sort_codes(pvgs)

    def _get_registry_version(self):
        return self.registry.version.strip()

    def _create_section_map(self, section_code):
        section_map = {}
        try:
            section_model = Section.objects.get(code=section_code)
            section_map["display_name"] = section_model.display_name
            section_map["questionnaire_display_name"] = section_model.questionnaire_display_name
            section_map["code"] = section_model.code
            section_map["extra"] = section_model.extra
            section_map["allow_multiple"] = section_model.allow_multiple
            section_map["elements"] = section_model.get_elements()
            section_map["questionnaire_help"] = section_model.questionnaire_help
        except Section.DoesNotExist:
            logger.error(f"Section not found: {section_code}")
        return section_map

    def _create_form_map(self, form_model):
        frm_map = {}
        frm_map["name"] = form_model.name
        frm_map["display_name"] = form_model.display_name
        frm_map["header"] = form_model.header
        frm_map["questionnaire_display_name"] = form_model.questionnaire_display_name
        frm_map["is_questionnaire"] = form_model.is_questionnaire
        frm_map["questionnaire_questions"] = form_model.questionnaire_questions
        frm_map["position"] = form_model.position
        frm_map["sections"] = []
        frm_map["applicability_condition"] = form_model.applicability_condition

        for section_code in form_model.get_sections():
            frm_map["sections"].append(self._create_section_map(section_code))

        return frm_map

    def _get_forms_allowed_groups(self):
        d = {}

        for form in self.registry.forms:
            d[form.name] = [g.name for g in form.groups_allowed.order_by("name")]
        return d

    def _export(self, format, export_type):
        data = {}
        data["RDRF_VERSION"] = VERSION
        data["EXPORT_TYPE"] = export_type
        data["EXPORT_TIME"] = str(datetime.datetime.now())
        data["cdes"] = list(map(cde_to_dict, self._get_cdes(export_type)))
        data["pvgs"] = [pvg.as_dict() for pvg in self._get_pvgs(export_type)]
        data["REGISTRY_VERSION"] = self._get_registry_version()
        data["metadata_json"] = self.registry.metadata_json
        data["consent_sections"] = self._get_consent_sections()
        data["forms_allowed_groups"] = self._get_forms_allowed_groups()
        data["demographic_fields"] = self._get_demographic_fields()
        data["complete_fields"] = self._get_complete_fields()
        data["reports"] = self._get_reports()
        data["cde_policies"] = self._get_cde_policies()
        data["context_form_groups"] = self._get_context_form_groups()
        data["email_notifications"] = self._get_email_notifications()
        data["consent_rules"] = self._get_consent_rules()
        data["surveys"] = self._get_surveys()
        data["reviews"] = self._get_reviews()
        data["custom_actions"] = self._get_custom_actions()
        data["hl7_mappings"] = self._get_hl7_mappings()

        if self.registry.patient_data_section:
            data["patient_data_section"] = self._create_section_map(
                self.registry.patient_data_section.code)
        else:
            data["patient_data_section"] = {}

        if export_type in [
                ExportType.REGISTRY_ONLY,
                ExportType.REGISTRY_PLUS_ALL_CDES,
                ExportType.REGISTRY_PLUS_CDES]:
            data["name"] = self.registry.name
            data["code"] = self.registry.code
            data["desc"] = self.registry.desc
            data["splash_screen"] = self.registry.splash_screen
            data["forms"] = []
            data["generic_sections"] = []
            for section_code in self.registry.generic_sections:
                data["generic_sections"].append(self._create_section_map(section_code))

            for frm in RegistryForm.objects.filter(registry=self.registry).order_by("name"):
                if frm.name == self.registry.generated_questionnaire_name:
                    # don't export the generated questionnaire
                    continue
                data["forms"].append(self._create_form_map(frm))

        if format == ExportFormat.YAML:
            try:
                export_data = dump_yaml(data)
            except Exception:
                logger.exception("Error yaml dumping")
                export_data = None
        elif format == ExportFormat.JSON:
            export_data = json.dumps(data)
        elif format is None:
            export_data = data
        else:
            raise Exception("Unknown format: %s" % format)

        return export_data

    def export_cdes_yaml(self, all_cdes=False):
        """
        Export common data element definitions

        :param all_cdes: if True export all CDEs in the database. If False(default)
        Then export only the CDEs used by the self.registry
        :return: return YAML file of all CDEs
        """
        return self._export_cdes(all_cdes, ExportFormat.YAML)

    def _export_cdes(self, all_cdes):
        if all_cdes:
            cdes = CommonDataElement.objects.order_by("code")
        else:
            cdes = self._get_cdes_in_registry(self.registry)

        data = {}

        if all_cdes:
            data["registry"] = "*"
        else:
            data["registry"] = self.registry.code

        data["cdes"] = []
        data["value_groups"] = []

        groups_used = set([])

        for cde_model in cdes:
            cde_map = {}
            cde_map["code"] = cde_model.code
            cde_map["name"] = cde_model.name
            cde_map["desc"] = cde_model.desc
            cde_map["datatype"] = cde_model.datatype
            cde_map["instructions"] = cde_model.instructions

            if cde_model.pv_group:
                cde_map["pv_group"] = cde_model.pv_group.code
                groups_used.add(cde_model.pv_group.code)
            else:
                cde_map["pv_group"] = ""

            cde_map["allow_multiple"] = cde_model.allow_multiple
            cde_map["max_length"] = cde_model.max_length
            cde_map["min_value"] = str(cde_model.min_value)
            cde_map["max_value"] = str(cde_model.max_value)
            cde_map["is_required"] = cde_model.is_required
            cde_map["important"] = cde_model.important
            cde_map["pattern"] = cde_model.pattern
            cde_map["widget_name"] = cde_model.widget_name
            cde_map["calculation"] = cde_model.calculation
            cde_map["questionnaire_text"] = cde_model.questionnaire_text
            cde_map["abnormality_condition"] = cde_model.abnormality_condition

            data["cdes"].append(cde_map)

        for group_code in groups_used:
            group_map = {}

            pvg = CDEPermittedValueGroup.objects.get(code=group_code)
            group_map["code"] = pvg.code
            group_map["values"] = []
            for value in CDEPermittedValue.objects.filter(
                    pv_group=pvg).order_by("position", "code"):
                value_map = {}
                value_map["code"] = value.code
                value_map["value"] = value.value
                value_map["questionnaire_value"] = value.questionnaire_value
                value_map["desc"] = value.desc
                value_map["position"] = value.position

                group_map["values"].append(value_map)

            data["value_groups"].append(group_map)

        if format == ExportFormat.YAML:
            export_cde__data = dump_yaml(data)
        elif format == ExportFormat.JSON:
            export_cde__data = json.dumps(data)
        else:
            raise Exception("Unknown format: %s" % format)

        return export_cde__data

    def _get_cdes_in_registry(self, registry_model):
        cdes = set([])
        for registry_form in RegistryForm.objects.filter(registry=registry_model):
            section_codes = registry_form.get_sections()
            cdes = cdes.union(self._get_cdes_for_sections(section_codes))

        if registry_model.patient_data_section:
            patient_data_section_cdes = set(registry_model.patient_data_section.cde_models)
        else:
            patient_data_section_cdes = set([])

        cdes = cdes.union(patient_data_section_cdes)

        generic_cdes = self._get_generic_cdes()
        cdes = cdes.union(generic_cdes)

        survey_cdes = self._get_survey_cdes()
        cdes = cdes.union(survey_cdes)

        return self._sort_codes(cdes)

    def _get_survey_cdes(self):
        # ensure if a registry has (proms) surveys we're exporting relevant cdes
        from rdrf.models.proms.models import Survey
        cdes = set([])
        for survey_model in Survey.objects.filter(registry=self.registry):
            for survey_question in survey_model.survey_questions.all():
                cde_model = CommonDataElement.objects.get(code=survey_question.cde.code)
                cdes.add(cde_model)
                if survey_question.precondition:
                    precondition_cde_model = CommonDataElement.objects.get(code=survey_question.precondition.cde.code)
                    cdes.add(precondition_cde_model)
        return cdes

    def _get_consent_sections(self):
        section_dicts = []
        for consent_section in self.registry.consent_sections.order_by("code"):
            section_dict = {"code": consent_section.code,
                            "section_label": consent_section.section_label,
                            "information_link": consent_section.information_link,
                            "information_text": consent_section.information_text,
                            "applicability_condition": consent_section.applicability_condition,
                            "validation_rule": consent_section.validation_rule,
                            "questions": []}
            for consent_model in consent_section.questions.order_by("position", "code"):
                cm = {"code": consent_model.code,
                      "position": consent_model.position,
                      "question_label": consent_model.question_label,
                      "questionnaire_label": consent_model.questionnaire_label,
                      "instructions": consent_model.instructions}
                section_dict["questions"].append(cm)
            section_dicts.append(section_dict)

        return section_dicts

    def _get_cdes_for_sections(self, section_codes):
        cdes = set([])
        for section_code in section_codes:
            try:
                section_model = Section.objects.get(code=section_code)
                section_cde_codes = section_model.get_elements()
                for cde_code in section_cde_codes:
                    try:
                        cde = CommonDataElement.objects.get(code=cde_code)
                        cdes.add(cde)
                    except CommonDataElement.DoesNotExist:
                        logger.error("No CDE with code: %s" % cde_code)

            except Section.DoesNotExist:
                logger.error("No Section with code: %s" % section_code)
        return cdes

    def _get_generic_cdes(self):
        return self._get_cdes_for_sections(self.registry.generic_sections)

    def _get_working_groups(self):
        from registry.groups.models import WorkingGroup
        return [wg.name for wg in WorkingGroup.objects.filter(registry=self.registry)]

    def _get_hl7_mappings(self):
        from intframework.models import HL7Mapping
        hl7_mappings = []
        for hl7_mapping in HL7Mapping.objects.all():
            hl7_dict = {"event_code": hl7_mapping.event_code,
                        "event_map": hl7_mapping.event_map}
            hl7_mappings.append(hl7_dict)
        return hl7_mappings

    def _get_demographic_fields(self):
        demographic_fields = []

        for demographic_field in DemographicFields.objects.filter(registry=self.registry):
            fields = {}
            fields['registry'] = demographic_field.registry.code
            fields['group'] = demographic_field.group.name
            fields['field'] = demographic_field.field
            fields['hidden'] = demographic_field.hidden
            fields['readonly'] = demographic_field.readonly
            demographic_fields.append(fields)

        return demographic_fields

    def _get_complete_fields(self):
        forms = RegistryForm.objects.filter(registry=self.registry)
        complete_fields = []

        for form in forms:
            if form.complete_form_cdes.exists():
                form_cdes = {}
                form_cdes["form_name"] = form.name
                form_cdes["cdes"] = [
                    cde.code for cde in form.complete_form_cdes.order_by("code")]
                complete_fields.append(form_cdes)

        return complete_fields

    def _get_reports(self):
        registry_queries = Query.objects.filter(registry=self.registry)

        queries = []
        for query in registry_queries:
            q = {}
            q["registry"] = query.registry.code
            q["access_group"] = [ag.name for ag in query.access_group.order_by("name")]
            q["title"] = query.title
            q["description"] = query.description
            q["mongo_search_type"] = query.mongo_search_type
            q["sql_query"] = query.sql_query
            q["collection"] = query.collection
            q["criteria"] = query.criteria
            q["projection"] = query.projection
            q["aggregation"] = query.aggregation
            q["created_by"] = query.created_by
            q["created_at"] = query.created_at
            queries.append(q)

        return queries

    def _get_cde_policies(self):
        from rdrf.models.definition.models import CdePolicy
        cde_policies = []
        for cde_policy in CdePolicy.objects.filter(
                registry=self.registry).order_by("cde__code"):
            cde_pol_dict = {}
            cde_pol_dict["cde_code"] = cde_policy.cde.code
            cde_pol_dict["groups_allowed"] = [
                group.name for group in cde_policy.groups_allowed.order_by("name")]
            cde_pol_dict["condition"] = cde_policy.condition
            cde_policies.append(cde_pol_dict)
        return cde_policies

    def _get_context_form_groups(self):
        from rdrf.models.definition.models import ContextFormGroup
        data = []
        for cfg in ContextFormGroup.objects.filter(registry=self.registry).order_by("name"):
            cfg_dict = {}
            cfg_dict["context_type"] = cfg.context_type
            cfg_dict["name"] = cfg.name
            cfg_dict["naming_scheme"] = cfg.naming_scheme
            cfg_dict["is_default"] = cfg.is_default
            cfg_dict["naming_cde_to_use"] = cfg.naming_cde_to_use
            cfg_dict["forms"] = []
            for form in cfg.forms:
                cfg_dict["forms"].append(form.name)
            cfg_dict["ordering"] = cfg.ordering
            data.append(cfg_dict)
        return data

    def _get_email_notifications(self):
        from rdrf.models.definition.models import EmailNotification
        data = []

        def get_template_dict(t):
            return {"language": t.language,
                    "description": t.description,
                    "subject": t.subject,
                    "body": t.body}

        for email_notification in EmailNotification.objects.filter(
                registry=self.registry).order_by("description"):
            en_dict = {}
            en_dict["description"] = email_notification.description
            en_dict["email_from"] = email_notification.email_from
            en_dict["recipient"] = email_notification.recipient
            if email_notification.group_recipient:
                en_dict["group_recipient"] = email_notification.group_recipient.name
            else:
                en_dict["group_recipient"] = None
            en_dict["email_templates"] = [get_template_dict(t) for t in
                                          email_notification.email_templates.all()]

            en_dict["disabled"] = email_notification.disabled
            data.append(en_dict)
        return data

    def _get_consent_rules(self):
        from rdrf.models.definition.models import ConsentRule
        data = []
        for consent_rule in ConsentRule.objects.filter(registry=self.registry):
            consent_rule_dict = {}
            consent_rule_dict["user_group"] = consent_rule.user_group.name
            consent_rule_dict["capability"] = consent_rule.capability
            consent_rule_dict["consent_section_code"] = consent_rule.consent_question.section.code
            consent_rule_dict["consent_question_code"] = consent_rule.consent_question.code
            consent_rule_dict["enabled"] = consent_rule.enabled
            data.append(consent_rule_dict)
        return data

    def _get_surveys(self):
        from rdrf.models.proms.models import Survey
        data = []
        for survey_model in Survey.objects.filter(registry=self.registry):
            survey_dict = {}
            survey_dict["name"] = survey_model.name
            survey_dict["display_name"] = survey_model.display_name
            survey_dict["questions"] = []
            survey_dict["is_followup"] = survey_model.is_followup
            if survey_model.context_form_group:
                cfg = survey_model.context_form_group.name
            else:
                cfg = ""
            survey_dict["context_form_group"] = cfg

            if survey_model.form:
                survey_dict["form"] = survey_model.form.name
            else:
                survey_dict["form"] = ""

            for sq in survey_model.survey_questions.all():
                sq_dict = {}
                sq_dict["cde"] = sq.cde.code
                sq_dict["cde_path"] = sq.cde_path
                sq_dict["title"] = sq.title
                sq_dict["position"] = sq.position
                sq_dict["precondition"] = None
                sq_dict["instruction"] = sq.instruction
                sq_dict["copyright_text"] = sq.copyright_text
                sq_dict["source"] = sq.source
                sq_dict["widget_config"] = sq.widget_config
                if sq.precondition:
                    sq_dict["precondition"] = {"cde": sq.precondition.cde.code,
                                               "value": sq.precondition.value}
                survey_dict["questions"].append(sq_dict)
            data.append(survey_dict)
        return data

    def _get_reviews(self):
        from rdrf.models.definition.review_models import Review
        review_dicts = []
        for review_model in Review.objects.filter(registry=self.registry).order_by("name"):
            review_dict = {}
            review_dict["name"] = review_model.name
            review_dict["code"] = review_model.code
            review_dict["review_type"] = review_model.review_type
            review_dict["items"] = []
            for review_item in review_model.items.all().order_by("position"):
                item_dict = {}
                item_dict["position"] = review_item.position
                item_dict["item_type"] = review_item.item_type
                item_dict["category"] = review_item.category
                item_dict["name"] = review_item.name
                item_dict["code"] = review_item.code
                item_dict["form"] = ""
                if review_item.form:
                    item_dict["form"] = review_item.form.name
                item_dict["section"] = ""
                if review_item.section:
                    item_dict["section"] = review_item.section.code
                item_dict["target_code"] = review_item.target_code
                item_dict["fields"] = review_item.fields
                item_dict["summary"] = review_item.summary
                item_dict["appearance_condition"] = review_item.appearance_condition
                review_dict["items"].append(item_dict)
            review_dicts.append(review_dict)
        return review_dicts

    def _get_custom_actions(self):
        from rdrf.models.definition.models import CustomAction
        actions = []
        for action in CustomAction.objects.filter(registry=self.registry):
            action_dict = {}
            action_dict["code"] = action.code
            action_dict["name"] = action.name
            action_dict["scope"] = action.scope
            action_dict["include_all"] = action.include_all
            action_dict["action_type"] = action.action_type
            action_dict["groups_allowed"] = [g.name for g in action.groups_allowed.all()]
            action_dict["data"] = action.data
            action_dict["runtime_spec"] = action.runtime_spec
            actions.append(action_dict)
        return actions


def str_presenter(dumper, data):
    lines = data.splitlines()
    if len(lines) > 1:
        # strip trailing whitespace on lines -- it's not significant,
        # and otherwise the dumper will use the quoted and escaped
        # string style.
        data = "\n".join(map(str.rstrip, lines))
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="|")
    else:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)


class ExportDumper(yaml.SafeDumper):
    pass


ExportDumper.add_representer(str, str_presenter)


def dump_yaml(data):
    return yaml.dump(data, Dumper=ExportDumper, allow_unicode=True,
                     default_flow_style=False)
