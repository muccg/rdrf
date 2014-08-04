from models import RegistryForm, Section, CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue
import logging
import yaml
import json
from django.conf import settings
from django.forms.models import model_to_dict
from rdrf import VERSION

import datetime



logger = logging.getLogger("registry_log")

class ExportException(Exception):
    pass

class ExportFormat:
    JSON = "JSON"
    YAML = "YAML"

class ExportType:
    REGISTRY_ONLY = "REGISTRY_ONLY"             # Only registry, forms , sections - No CDEs
    REGISTRY_PLUS_CDES = "REGISTRY_PLUS_CDES"   # As above with cdes used by the registry
    REGISTRY_PLUS_ALL_CDES = "REGISTRY_PLUS_ALL_CDES" # registry + all cdes in the site
    REGISTRY_CDES = "REGISTRY_CDES" # only the cdes in the supplied registry ( no forms)
    ALL_CDES = "ALL_CDES" # All CDEs in the site

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
        except Exception, ex:
            return None, [ex]



    def export_json(self):
        return self._export(ExportFormat.JSON)

    def _get_cdes(self, export_type):
        if export_type == ExportType.REGISTRY_ONLY:
            cdes = set([])
        elif export_type in [ ExportType.REGISTRY_PLUS_CDES, ExportType.REGISTRY_CDES]:
            cdes = set([ cde for cde in self._get_cdes_in_registry(self.registry) ])
        elif export_type in [ ExportType.ALL_CDES, ExportType.REGISTRY_PLUS_ALL_CDES]:
            cdes = set([ cde for cde in CommonDataElement.objects.all() ])
        else:
            raise ExportException("Unknown export type")
        return cdes


    def _get_pvgs_in_registry(self, registry):
        pvgs = set([])

        for cde in self._get_cdes_in_registry(registry):
            if cde.pv_group:
                pvgs.add(cde.pv_group)
        return pvgs

    def _get_pvgs(self, export_type):
        if export_type == ExportType.REGISTRY_ONLY:
            pvgs = set([])
        elif export_type in [ ExportType.REGISTRY_PLUS_CDES, ExportType.REGISTRY_CDES]:
            pvgs = set([ pvg for pvg in  self._get_pvgs_in_registry(self.registry) ])
        elif export_type in [ ExportType.ALL_CDES, ExportType.REGISTRY_PLUS_ALL_CDES]:
            pvgs = set([ pvg for pvg  in CDEPermittedValueGroup.objects.all() ])
        else:
            raise ExportException("Unknown export type")
        return pvgs

    def _get_registry_version(self):
        return self.registry.version.strip()

    def _export(self,format, export_type):
        data = {}

        data["RDRF_VERSION"] = VERSION
        data["EXPORT_TYPE"] = export_type
        data["EXPORT_TIME"] = str(datetime.datetime.now())
        data["cdes"] = [ model_to_dict(cde) for cde in self._get_cdes(export_type) ]
        data["pvgs"] = [ pvg.as_dict() for pvg in self._get_pvgs(export_type) ]
        data["REGISTRY_VERSION"] = self._get_registry_version()


        if export_type in [ ExportType.REGISTRY_ONLY, ExportType.REGISTRY_PLUS_ALL_CDES, ExportType.REGISTRY_PLUS_CDES]:
            data["name"] = self.registry.name
            data["code"] = self.registry.code
            data["splash_screen"] = self.registry.splash_screen
            data["forms"] = []

            for frm in RegistryForm.objects.all().filter(registry=self.registry):
                frm_map = {}
                frm_map["name"] = frm.name
                frm_map["is_questionnaire"] = frm.is_questionnaire
                frm_map["sections"] = []
                for section_code in frm.get_sections():
                    section_model = Section.objects.get(code=section_code)
                    section_map = {}
                    section_map["display_name"] = section_model.display_name
                    section_map["code"] = section_model.code
                    section_map["extra"] = section_model.extra
                    section_map["allow_multiple"] = section_model.allow_multiple
                    section_map["elements"] = section_model.get_elements()
                    frm_map["sections"].append(section_map)
                data["forms"].append(frm_map)

        if format == ExportFormat.YAML:
            logger.debug("About to yaml dump the export: data = %s" % data)
            try:
                export_data = yaml.dump(data)
            except Exception,ex:
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

    def _export_cdes(self,all_cdes):
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
            for section_code in section_codes:
                logger.debug("getting cdes in section %s" % section_code)
                try:
                    section_model = Section.objects.get(code=section_code)
                    section_cde_codes = section_model.get_elements()
                    for cde_code in section_cde_codes:
                        try:
                            cde = CommonDataElement.objects.get(code=cde_code)
                            cdes.add(cde)
                        except CommonDataElement.DoesNotExist,ex:
                            logger.error("No CDE with code: %s" % cde_code)

                except Section.DoesNotExist,ex:
                    logger.error("No Section with code: %s" % section_code)



        return cdes



















