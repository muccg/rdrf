from models import RegistryForm, Section
import logging

logger = logging.getLogger("registry")

class ExportFormat:
    JSON = "JSON"
    YAML = "YAML"

class Exporter(object):
    """
    Export a registry definition to yaml or json
    """
    def __init__(self, registry_model):
        self.registry = registry_model

    def export_yaml(self):
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




        :return: a yaml file containing the definition of a registry ( i
        """
        return self._export(ExportFormat.YAML)

    def export_json(self):
        return self._export(ExportFormat.JSON)



    def _export(self,format):
        data = {}
        data["name"] = self.name
        data["code"] = self.code
        data["splash_screen"] = "todo"
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
            import yaml
            export_data = yaml.dump(data)
        elif format == ExportFormat.JSON:
            import json
            export_data = json.dumps(data)
        elif format is None:
            export_data = data
        else:
            raise Exception("Unknown format: %s" % format)

        logger.debug("Export of Registry %s" % self.name)
        logger.debug("Format = %s" % format)
        logger.debug("Export Data:")
        logger.debug("%s" % export_data)

        return export_data
