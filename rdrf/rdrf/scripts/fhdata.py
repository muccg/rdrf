import yaml
import sys
import csv
from string import strip


class DemographicForm:
    SECTION_REGISTRY = "Registry"
    SECTION_PATIENT_DETAILS = "Patients Personal Details"
    


class DemographicField(object):
    def __init__(self, section, name, datatype="STRING", members=[], validation=""):
        self.name = name
        self.section = section
        self.members = members
        self.validation = validation

        if self.datatype == "DATE":
            self.validation = "dd/mm/yyyy"


class CDEWrapper(object):
    def __init__(self, data, cde_dict):
        self.data = data
        self.cde_dict = cde_dict

    @property
    def name(self):
        return self.cde_dict["name"]
    

    @property
    def datatype(self):
        return self.cde_dict["datatype"].strip().upper()
    
    @property
    def members(self):
        if self.datatype == "RANGE":
            return "|".join(self._get_allowed_values())
        else:
            return ""


    @property
    def validation(self):
        vals = []
        if self.datatype == "STRING":
            if self.cde_dict["max_length"]:
                vals.append("Length <= %s" % self.cde_dict["max_length"])
            if self.cde_dict["pattern"]:
                vals.append("Must conform to regular expression %s" % self.cde_dict["pattern"])
        elif self.datatype == "INTEGER":
            if self.cde_dict["min_value"]:
                vals.append("Minimum value = %s" % self.cde_dict["min_value"])
            if self.cde_dict["max_value"]:
                vals.append("Maximum value = %s" % self.cde_dict["max_value"])
        return ",".join(vals)
            

    def _get_allowed_values(self):
        pvg_code = self.cde_dict["pv_group"]
        if pvg_code:
            for pvg in self.data["pvgs"]:
                if pvg_code == pvg["code"]:
                    mappings = []
                    for pv in pvg["values"]:
                        stored_value = pv["value"]
                        display_value = pv["code"]
                        mapping = "%s(%s)" % (stored_value, display_value)
                        mappings.append(mapping)
                    return mappings
            return []
        else:
            return []
            
            
class DataDefinitionReport(object):
    def __init__(self, data, stream):
        self.data = data
        self.stream = stream
        self.current_line = []
        self.line_num = 1
        self.delimiter = "\t"

    def write_column(self, value):
        self.current_line.append(value)

    def new_line(self):
        line = self.delimiter.join(self.current_line)
        line = line + "\n"
        line = line.encode('ascii', 'ignore')
        self.stream.write(line)
        self.current_line = []
        self.line_num += 1

    def write_values(self, *values):
        for value in values:
            self.write_column(value)

        self.new_line()
        
    def write_header(self):
        self.write_values("FORM","SECTION","CDE","DATATYPE","ALLOWED VALUES", "VALIDATION")


    def _get_cdes_from_section(self, section_dict):
        cdes = []
        cde_codes = map(strip, section_dict["elements"])
        for cde_code in cde_codes:
            cde_dict = self._get_cde_dict(cde_code)
            cde = CDEWrapper(self.data, cde_dict)
            cdes.append(cde)
        return cdes

    def _get_cde_dict(self, cde_code):
        for cde_dict in self.data["cdes"]:
            if cde_dict["code"] == cde_code:
                return cde_dict

    def _get_demographic_fields(self):
        fields = []
        fields.append(DemographicField(DemographicForm.SECTION_REGISTRY, "Centre"))
        #fields.append(DemographicField(DemographicForm.SECTION_REGISTRY, "Clinician"))
        fields.append(DemographicField(DemographicForm.SECTION_PATIENT_DETAILS, "Family name"))
        fields.append(DemographicField(DemographicForm.SECTION_PATIENT_DETAILS, "Given names"))
        fields.append(DemographicField(DemographicForm.SECTION_PATIENT_DETAILS, "Maiden name"))
        
                      
                      
        return fields

    def __iter__(self):
        for demographic_field in self._get_demographic_fields():
            yield "DEMOGRAPHICS", demographic_field.section, demographic_field.field,demographic_field.datatype, demographic_field.members, demographic_field.validation
        
        for form_dict in self.data["forms"]:
            for section_dict in form_dict["sections"]:
                if not section_dict["allow_multiple"]:
                    cdes = self._get_cdes_from_section(section_dict)
                    for cde in cdes:
                        yield form_dict["name"], section_dict["display_name"], cde.name, cde.datatype, cde.members, cde.validation
                    

yaml_file = sys.argv[1]
output_file = sys.argv[2]



with open(yaml_file) as yf:
    data = yaml.load(yf)


with open(output_file, "w") as f:
    ddr = DataDefinitionReport(data, f)
    ddr.write_header()
    for items in ddr:
        ddr.write_values(*items)
