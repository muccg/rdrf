"""
Custom Module
For Issue 1007 Move CDEs from one section to another and migrate data on ClinicalData form
"""
import logging


logger = logging.getLogger(__name__)

def get_section(section_code, data_dict):
    for form in data_dict['forms']:
        if(form['name'] == "ClinicalData"):
            for section in form['sections']:
                if(section['code'] == section_code):
                    return section


def move_cdes(cde_code, source_section, target_section):
    # Get target cde dictionary
    # change it to have multi-value to cater
    source_cdes_list = source_section['cdes']
    if len(source_cdes_list) == 0:
        print("No items found in source section......")

    for i, source_cde_item in enumerate(source_cdes_list):
        for j, cde_dict in enumerate(source_cde_item):
            if cde_dict['code'] in cde_code:
                # Append to target section
                if i == 0 and target_section['allow_multiple'] is False:
                    target_section_item = target_section['cdes']
                    target_section_item.append(cde_dict.copy())
                    print("Adding %s to target section and will look as below" % str(cde_dict))
                    print(target_section_item)
                # Remove cde dict from source section
                removed_cde_dict = source_cde_item.pop(j)
                #print("Removing %s from source section and will look as below" % str(cde_dict))
                print("Removing %s from source section and will look as below" % str(removed_cde_dict))
                print(source_cde_item)


def tranform_data_dict(cd_data, *args):
    print(args)
    cdes_code = args[0]
    source_section_code = args[1]
    target_section_code = args[2]
    print("******* Transforming Cde=%s from section=%s to section=%s **************" % (cdes_code, source_section_code, target_section_code))
    new_data = cd_data.copy()
    source_section_dict = get_section(source_section_code, cd_data)
    target_section_dict = get_section(target_section_code, cd_data)
    # Check if both section exists and move CDEs
    if source_section_dict and target_section_dict:
        # for code in cdes_code:
        print("******* Migrating Cde=%s from section=%s to section=%s **************" % (cdes_code, source_section_code, target_section_code))
        move_cdes(cdes_code, source_section_dict, target_section_dict)
    else:
        print("Either source section %s or target section %s or both doesn't exists" % (source_section_code, target_section_code))
    return new_data
