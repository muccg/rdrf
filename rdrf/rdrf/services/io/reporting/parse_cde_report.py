from rdrf.models.definition.models import CDEPermittedValueGroup, CDEPermittedValue, CommonDataElement
from lxml import etree
import sys


class NINDSReportParser:
    CDE_CODE = 'textbox12'
    CDE_NAME = 'VariableName'
    CDE_DEFINITION = 'Definition'
    CDE_DATATYPE = 'textbox26'
    CDE_INSTRUCTIONS = 'textbox57'
    CDE_REFERENCES = 'textbox58'
    CDE_POPULATION = 'textbox81'
    CDE_CLASSIFICATION = 'textbox59'
    CDE_VERSION = 'VersionNumber'
    CDE_VERSION_DATE = 'VersionDate'
    CDE_VARIABLE_NAME = 'textbox74'
    CDE_VARIABLE_NAME_ALIASES = 'textbox67'
    CDE_SUBDOMAIN = 'textbox62'
    CDE_CRF_MODULE = 'textbox63'
    CDE_DOMAIN = 'textbox87'
    CDE_PV_CODE = 'textbox34'
    PVG_CODE = 'textbox22'
    PV_CODE = 'textbox34'
    PV_VALUE = 'textbox7'
    PV_DESC = 'textbox90'

    @classmethod
    def parse_pvg(cls, elem):
        pvg_code = elem.get(cls.PVG_CODE)
        # dummy element
        if pvg_code is None:
            return
        try:
            CDEPermittedValueGroup.objects.get(code__exact=pvg_code)
            print("PVG %s already exists." % pvg_code)
            return
        except CDEPermittedValueGroup.DoesNotExist:
            pass

        pvg = CDEPermittedValueGroup(code=pvg_code)
        pvg.save()

        print("Created: ", pvg)

        for detail in etree.ETXPath('./{rptAllCDE}Detail_Collection/{rptAllCDE}Detail')(elem):
            pv_code = detail.get(cls.PV_CODE)
            if pv_code is None:
                continue
            pv = CDEPermittedValue(
                code=detail.get(cls.PV_CODE),
                value=detail.get(cls.PV_VALUE),
                desc=detail.get(cls.PV_DESC),
                pv_group=pvg)
            print("Created:", pv)
            pv.save()

        return pvg

    @classmethod
    def parse_cde(cls, elem, pvg):
        cde_code = elem.get(cls.CDE_CODE)
        try:
            CommonDataElement.objects.get(code__exact=cde_code)
            print("CDE %s already exists." % cde_code)
            return
        except CommonDataElement.DoesNotExist:
            pass
        new_obj = CommonDataElement(
            code=cde_code,
            name=elem.get(cls.CDE_NAME),
            desc=elem.get(cls.CDE_DEFINITION),
            datatype=elem.get(cls.CDE_DATATYPE),
            instructions=elem.get(cls.CDE_INSTRUCTIONS),
            references=elem.get(cls.CDE_REFERENCES),
            population=elem.get(cls.CDE_POPULATION),
            classification=elem.get(cls.CDE_CLASSIFICATION),
            version=elem.get(cls.CDE_VERSION),
            version_date=(elem.get(cls.CDE_VERSION_DATE).split('T', 1))[0],
            variable_name=elem.get(cls.CDE_VARIABLE_NAME),
            aliases_for_variable_name=elem.get(cls.CDE_VARIABLE_NAME_ALIASES),
            crf_module=elem.get(cls.CDE_CRF_MODULE),
            subdomain=elem.get(cls.CDE_SUBDOMAIN),
            domain=elem.get(cls.CDE_DOMAIN),
            pv_group=pvg,
        )
        print("Created: ", new_obj)
        new_obj.save()

    @classmethod
    def parse_file(cls, xml_file):
        print("Parsing: " + xml_file)
        with open(xml_file, 'r') as fd:
            et = etree.parse(fd)
        for table1_group1 in etree.ETXPath(
                './{rptAllCDE}table1/{rptAllCDE}table1_Group1_Collection/{rptAllCDE}table1_Group1')(et.getroot()):
            pvg = None
            for table1_group2 in etree.ETXPath(
                    './{rptAllCDE}table1_Group2_Collection/{rptAllCDE}table1_Group2')(table1_group1):
                pvg = NINDSReportParser.parse_pvg(table1_group2)
            NINDSReportParser.parse_cde(table1_group1, pvg)


if __name__ == '__main__':
    for report_file in sys.argv[1:]:
        NINDSReportParser.parse_file(report_file)
