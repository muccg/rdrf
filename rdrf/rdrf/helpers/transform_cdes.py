"""
Custom Module
For Repo: rdrf and Issue#1007(in rdrf-ccg) Move CDEs from one section to another and migrate data on ClinicalData form
"""
import logging


logger = logging.getLogger(__name__)

def get_section(section_code, data_dict):
    # Assert if 'Forms' exist in data dictionary
    if 'forms' not in data_dict.keys():
        raise Exception("No forms found in data dictionary ......")

    for form in data_dict['forms']:
        if(form['name'] == "ClinicalData"):
            for section in form['sections']:
                if(section['code'] == section_code):
                    return section


def move_cdes(cde_codes, source_section, target_section):
    # Assert Source section is multi-value 
    if source_section['allow_multiple'] is not True:
        raise  Exception("Found Source section is single-value : %s " % (source_section))

    source_cdes_list = source_section['cdes']
    # Assert Source section has cdes
    if len(source_cdes_list) == 0:
        print("Found Source section is empty with no CDEs......")
        return
    # Assert Target section is single-value
    if target_section['allow_multiple'] is not False:
        raise Exception("Found Target section is multi-value : %s " % (target_section))
    target_section_item = target_section['cdes']
    
    for i, source_cde_item in enumerate(source_cdes_list):
        for j, cde_dict in enumerate(source_cde_item):
            if cde_dict['code'] in cde_codes:
                if i == 0:
                    # Append to target section
                    target_section_item.append(cde_dict.copy())
                    print("Adding %s to target section and will look as below" % str(cde_dict))
                    print(target_section_item)
                # Remove cde dict from source section
                removed_cde_dict = source_cde_item.pop(j)
                #print("Removing %s from source section and will look as below" % str(cde_dict))
                print("Removing %s from source section and will look as below" % str(removed_cde_dict))
                print(source_cde_item)


def tranform_data_dict(cde_codes, source_section_code, target_section_code, cd_data):
    # Getting both section first
    source_section_dict = get_section(source_section_code, cd_data)
    target_section_dict = get_section(target_section_code, cd_data)
    # Check if both section exists and move CDEs
    if source_section_dict and target_section_dict:
        # for code in cdes_code:
        print("******* Moving Cdes **************")
        move_cdes(cde_codes, source_section_dict, target_section_dict)
    else:
        print("Skipping cdes transformation: Either source section=%s or target section=%s (or both) does not exist in data dictionary" % (source_section_code, target_section_code))
        
    return cd_data
