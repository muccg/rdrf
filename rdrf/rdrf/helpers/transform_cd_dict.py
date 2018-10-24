"""
Custom Module
GitHub Repo: rdrf
Issue#1007(in rdrf-ccg repo)
Move CDEs from one section to another and migrate data on ClinicalData form
"""


def structure_valid(cde_codes, source_section_code, target_section_code, cd_data_dict):
    print(" Validating Structure ......")
    # Check if 'Forms' exist in cd_data dictionary
    if 'forms' not in cd_data_dict.keys():
        print("******* Skipping cdes movement...... No 'forms' found in data dictionary ...... %s" % cd_data_dict)
        return False
    # Check if clinical data form exist
    cd_form = get_cd_form(cd_data_dict)
    if not cd_form:
        print("******* Skipping cdes movement...... Couldn't find 'ClinicalData' form in data dictionary...... %s" % cd_data_dict)
        return False
    # Check if source section exist
    source_section_dict = get_section(source_section_code, cd_form)
    if not source_section_dict:
        print("******* Skipping cdes movement......Couldn't find source section with code=%s in 'ClinicalData' form: %s" % (source_section_code, cd_form))
        return False
    # Check if source section is multi-value
    if not source_section_dict['allow_multiple']:
        print("******* Skipping cdes movement......Source section is not multi-value : %s " % (source_section_dict))
        return False
    # Check if source section is not empty
    if not source_section_dict['cdes']:
        print("******* Skipping cdes movement...... Source section is empty.")
        return False
    # Check if target section exist
    target_section_dict = get_section(target_section_code, cd_form)
    if not target_section_dict:
        print("******* Skipping cdes movement......Couldn't find target section with code=%s in 'ClinicalData' form: %s" % (target_section_code, cd_form))
        return False
    # Check if target section is single-value
    if target_section_dict['allow_multiple']:
        print("******* Skipping cdes movement......Target section is not single-value: %s " % (target_section_dict))
        return False
    # Check if cdes (CDE00016,FHCRP) are not in target Section
    cdes_found_in_target_section = [cde for cde in target_section_dict['cdes'] if cde['code'] in cde_codes]
    if cdes_found_in_target_section:
        print("******* Skipping cdes movement...... Cdes=%s already exist in Target Section." % cdes_found_in_target_section)
        return False
    return True


def transform_cd_dict(cde_codes, source_section_code, target_section_code, cd_data_dict):
    print("@@@@@@@ Moving Cdes=%s from source section=%s to target section=%s in ClinicalData form @@@@@@@" % (cde_codes, source_section_code, target_section_code))
    print(" Getting ClinicalData form ......")
    # Get clinical data form
    cd_form = get_cd_form(cd_data_dict)
    print(" Getting source/target sections ......")
    # Get both sections from clinical data form
    source_section_dict = get_section(source_section_code, cd_form)
    print("******* Source section : %s" % source_section_dict)
    target_section_dict = get_section(target_section_code, cd_form)
    print("******* Target section : %s" % target_section_dict)
    print(" Moving CDES ......")
    move_cdes(cde_codes, source_section_dict, target_section_dict)
    return cd_data_dict


def get_cd_form(cd_data_dict):
    for form in cd_data_dict['forms']:
        if form['name'] == "ClinicalData":
            return form


def get_section(section_code, form):
    for section in form['sections']:
        if section['code'] == section_code:
            return section


def move_cdes(cde_codes, source_section, target_section):
    # Copy cdes from first item of source section
    cdes_to_move = [cde for cde in source_section['cdes'][0] if cde['code'] in cde_codes]
    print("******* CDEs to move (from first item only): %s" % cdes_to_move)
    print(" Removing cdes from source section ......")
    # Remove cdes from source section
    updated_source_section = [clean_cdes(cdes_list, cde_codes) for cdes_list in source_section['cdes']]
    source_section['cdes'] = updated_source_section
    print("******* Source section after movement: %s" % source_section)
    print(" Appending cdes to target section ......")
    # Append cdes to target section
    updated_target_section = target_section['cdes'] + cdes_to_move
    target_section['cdes'] = updated_target_section
    print("******* Target section after movement: %s" % target_section)
    print("@@@@@@@ CDE migration completed successfully @@@@@@@")


def clean_cdes(cdes_list, cde_codes):
    return [cde for cde in cdes_list if cde['code'] not in cde_codes]
