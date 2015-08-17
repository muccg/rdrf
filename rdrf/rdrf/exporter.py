from models import Section, CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue
import logging
import yaml
import json
from django.forms.models import model_to_dict
from rdrf import VERSION
import datetime
from rdrf.models import AdjudicationDefinition, DemographicFields, RegistryForm
from explorer.models import Query

logger = logging.getLogger("registry_log")


class ExportException(Exception):
    pass


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
            cdes = set([cde for cde in CommonDataElement.objects.all()])
        else:
            raise ExportException("Unknown export type")

        generic_cdes = self._get_generic_cdes()
        return cdes.union(generic_cdes)

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
            pvgs = set([pvg for pvg in CDEPermittedValueGroup.objects.all()])
        else:
            raise ExportException("Unknown export type")
        return pvgs

    def _get_registry_version(self):
        return self.registry.version.strip()

    def _create_section_map(self, section_code):
        section_model = Section.objects.get(code=section_code)
        section_map = {}
        section_map["display_name"] = section_model.display_name
        section_map["questionnaire_display_name"] = section_model.questionnaire_display_name
        section_map["code"] = section_model.code
        section_map["extra"] = section_model.extra
        section_map["allow_multiple"] = section_model.allow_multiple
        section_map["elements"] = section_model.get_elements()
        section_map["questionnaire_help"] = section_model.questionnaire_help
        return section_map

    def _create_form_map(self, form_model):
        frm_map = {}
        frm_map["name"] = form_model.name
        frm_map["questionnaire_display_name"] = form_model.questionnaire_display_name
        frm_map["is_questionnaire"] = form_model.is_questionnaire
        frm_map["questionnaire_questions"] = form_model.questionnaire_questions
        frm_map["sections"] = []

        for section_code in form_model.get_sections():
            frm_map["sections"].append(self._create_section_map(section_code))

        return frm_map

    def _get_forms_allowed_groups(self):
        d = {}

        for form in self.registry.forms:
            d[form.name] = [g.name for g in form.groups_allowed.all()]
        return d

    def _export(self, format, export_type):
        data = {}
        data["RDRF_VERSION"] = VERSION
        data["EXPORT_TYPE"] = export_type
        data["EXPORT_TIME"] = str(datetime.datetime.now())
        data["cdes"] = [model_to_dict(cde) for cde in self._get_cdes(export_type)]
        data["pvgs"] = [pvg.as_dict() for pvg in self._get_pvgs(export_type)]
        data["REGISTRY_VERSION"] = self._get_registry_version()
        data["metadata_json"] = self.registry.metadata_json
        data["adjudication_definitions"] = self._get_adjudication_definitions()
        data["consent_sections"] = self._get_consent_sections()
        data["forms_allowed_groups"] = self._get_forms_allowed_groups()
        data["demographic_fields"] = self._get_demographic_fields()
        data["complete_fields"] = self._get_complete_fields()
        data["reports"] = self._get_reports()
        data["cde_policies"] = self._get_cde_policies()

        if self.registry.patient_data_section:
            data["patient_data_section"] = self._create_section_map(
                self.registry.patient_data_section.code)
        else:
            data["patient_data_section"] = {}

        data["working_groups"] = self._get_working_groups()

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

            for frm in RegistryForm.objects.all().filter(registry=self.registry):
                if frm.name == self.registry.generated_questionnaire_name:
                    # don't export the generated questionnaire
                    continue
                data["forms"].append(self._create_form_map(frm))

        if format == ExportFormat.YAML:
            logger.debug("About to yaml dump the export: data = %s" % data)
            try:
                export_data = yaml.safe_dump(data, allow_unicode=True)
            except Exception as ex:
                logger.error("Error yaml dumping: %s" % ex)
                export_data = None
        elif format == ExportFormat.JSON:
            export_data = json.dumps(data)
        elif format is None:
            export_data = data
        else:
            raise Exception("Unknown format: %s" % format)

        logger.debug("Export of Registry %s" % self.registry.name)
        logger.debug("Format = %s" % format)
        logger.debug("Export Data:")
        logger.debug("%s" % export_data)
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
            cdes = CommonDataElement.objects.all()
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
            cde_map["min_value"] = cde_model.min_value
            cde_map["is_required"] = cde_model.is_required
            cde_map["pattern"] = cde_model.pattern
            cde_map["widget_name"] = cde_model.widget_name
            cde_map["calculation"] = cde_model.calculation
            cde_map["questionnaire_text"] = cde_model.questionnaire_text

            data["cdes"].append(cde_map)

        for group_code in groups_used:
            group_map = {}

            pvg = CDEPermittedValueGroup.objects.get(code=group_code)
            group_map["code"] = pvg.code
            group_map["values"] = []
            for value in CDEPermittedValue.objects.all().filter(pv_group=pvg):
                value_map = {}
                value_map["code"] = value.code
                value_map["value"] = value.value
                value_map["questionnaire_value"] = value.questionnaire_value
                value_map["desc"] = value.desc
                value_map["position"] = value.position

                group_map["values"].append(value_map)

            data["value_groups"].append(group_map)

        if format == ExportFormat.YAML:
            export_cde__data = yaml.dump(data)
        elif format == ExportFormat.JSON:
            export_cde__data = json.dumps(data)
        else:
            raise Exception("Unknown format: %s" % format)

        return export_cde__data

    def _get_cdes_in_registry(self, registry_model):
        cdes = set([])
        for registry_form in RegistryForm.objects.filter(registry=registry_model):
            logger.debug("getting cdes for form %s" % registry_form)
            section_codes = registry_form.get_sections()
            cdes = cdes.union(self._get_cdes_for_sections(section_codes))

        if registry_model.patient_data_section:
            patient_data_section_cdes = set(registry_model.patient_data_section.cde_models)
        else:
            patient_data_section_cdes = set([])

        cdes = cdes.union(patient_data_section_cdes)

        generic_cdes = self._get_generic_cdes()
        adjudication_cdes = self._get_adjudication_cdes()
        cdes = cdes.union(generic_cdes)
        cdes = cdes.union(adjudication_cdes)

        return cdes

    def _get_consent_sections(self):
        section_dicts = []
        for consent_section in self.registry.consent_sections.all():
            section_dict = {"code": consent_section.code,
                            "section_label": consent_section.section_label,
                            "information_link": consent_section.information_link,
                            "applicability_condition": consent_section.applicability_condition,
                            "validation_rule": consent_section.validation_rule,
                            "questions": []}
            for consent_model in consent_section.questions.all():
                cm = {"code": consent_model.code,
                      "position": consent_model.position,
                      "question_label": consent_model.question_label,
                      "questionnaire_label": consent_model.questionnaire_label,
                      "instructions": consent_model.instructions}
                section_dict["questions"].append(cm)
            section_dicts.append(section_dict)

        return section_dicts

    def _get_adjudication_cdes(self):
        adjudication_cdes = set([])
        for adj_def in AdjudicationDefinition.objects.filter(registry=self.registry):
            # points to a section containing cdes which capture adjucation ratings
            adjudication_section_code = adj_def.result_fields
            # points to a section containing decision fields ( which are mapped to actions )
            result_section_code = adj_def.decision_field
            adjudication_cdes = adjudication_cdes.union(
                self._get_cdes_for_sections([adjudication_section_code, result_section_code]))
        return adjudication_cdes

    def _get_cdes_for_sections(self, section_codes):
        cdes = set([])
        for section_code in section_codes:
            logger.debug("getting cdes in section %s" % section_code)
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

    def _get_adjudication_definitions(self):
        """
        fields = models.TextField()
        result_fields = models.TextField() # section_code containing cde codes of result
        decision_field = models.TextField(blank=True, null=True) # cde code of a range field with allowed actions
        adjudicator_username = models.CharField(max_length=80, default="admin")  # an admin user to check the incoming
        :return:
        """
        adj_def_maps = []

        def get_section_maps(adj_def):
            result_fields_section = self._create_section_map(adj_def.result_fields)
            decision_fields_section = self._create_section_map(adj_def.decision_field)
            return {
                "results_fields": result_fields_section,
                "decision_fields_section": decision_fields_section}

        for adj_def in AdjudicationDefinition.objects.filter(registry=self.registry):
            adj_def_map = {}
            adj_def_map['fields'] = adj_def.fields
            adj_def_map['result_fields'] = adj_def.result_fields
            adj_def_map['decision_field'] = adj_def.decision_field   # section for dec
            adj_def_map['adjudicator_username'] = adj_def.adjudicator_username
            adj_def_map["adjudicating_users"] = adj_def.adjudicating_users
            adj_def_map["display_name"] = adj_def.display_name
            adj_def_map["sections_required"] = get_section_maps(adj_def)
            adj_def_maps.append(adj_def_map)

        return adj_def_maps

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
                form_cdes["cdes"] = [cde.code for cde in form.complete_form_cdes.all()]
                complete_fields.append(form_cdes)

        return complete_fields

    def _get_reports(self):
        registry_queries = Query.objects.filter(registry=self.registry)

        queries = []
        for query in registry_queries:
            q = {}
            q["registry"] = query.registry.code
            q["access_group"] = [ag.id for ag in query.access_group.all()]
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
        from rdrf.models import CdePolicy
        cde_policies = []
        for cde_policy in CdePolicy.objects.filter(registry=self.registry):
            cde_pol_dict = {}
            cde_pol_dict["cde_code"] = cde_policy.cde.code
            cde_pol_dict["groups_allowed"] = [group.name for group in cde_policy.groups_allowed.all()]
            cde_pol_dict["condition"] = cde_policy.condition
            cde_policies.append(cde_pol_dict)
        return cde_policies
