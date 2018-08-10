"""
Custom Module
GitHub Repo: rdrf 
Issue#1007(in rdrf-ccg repo) 
Move CDEs from one section to another and migrate data on ClinicalData form
"""
         

def tranform_data_dict(cde_codes, source_section_code, target_section_code, cd_data_dict):
    print(" Finding ClinicalData form ......")
    # Check if 'Forms' exist in cd_data dictionary
    if 'forms' not in cd_data_dict.keys():
        raise Exception("******* No 'forms' found in data dictionary ...... %s" % cd_data_dict)        
    # Get clinical data form
    cd_form = 0
    for form in cd_data_dict['forms']:
        if form['name'] == "ClinicalData":
            cd_form = form
    if not cd_form:
        print("******* Skipping cdes movement...... Couldn't find 'ClinicalData' form in data dictionary...... %s" % cd_data_dict)
        return
    print("@@@@@@@ Moving Cdes=%s from source section=%s to target section=%s in ClinicalData form @@@@@@@" 
            % (cde_codes, source_section_code, target_section_code))
    print(" Getting both sections ......")
    # Get both sections from clinical data form
    source_section_dict = get_section(source_section_code, cd_form)
    print("******* Source section : %s" % source_section_dict)
    target_section_dict = get_section(target_section_code, cd_form)
    print("******* Target section : %s" % target_section_dict)
    
    if not source_section_dict:
        print("******* Skipping cdes movement......Couldn't find source section with code=%s in 'ClinicalData' form: %s" % (source_section_code, cd_form)) 
        return cd_data_dict
    if not target_section_dict:
        print("******* Skipping cdes movement......Couldn't find target section with code=%s in 'ClinicalData' form: %s" % (target_section_code, cd_form)) 
        return cd_data_dict

    move_cdes(cde_codes, source_section_dict, target_section_dict)

    return cd_data_dict


def get_section(section_code, form):
    section_found = 0
    for section in form['sections']:
        if section['code'] == section_code:
            section_found = section
    return section_found


def move_cdes(cde_codes, source_section, target_section):
    # Check if source section is multi-value
    if not source_section['allow_multiple']:
        raise Exception("******* Couldn't move cdes......Found Source section is single-value : %s "
                        % (source_section))
    # Check if source section is not empty 
    if not source_section['cdes']:
        print("******* Skipping cdes movement...... Source section is empty.")
        return
    # Check if target section is single-value
    if target_section['allow_multiple']:
        raise Exception("******* Couldn't move cdes......Found Target section is multi-value: %s "
                        % (target_section))
    # Check if cdes (CDE00016,FHCRP) are not in target Section
    cdes_found_in_target_section = [cde for cde in target_section['cdes'] if cde['code'] in cde_codes]
    if cdes_found_in_target_section:
        print("******* Skipping cdes movement...... Cdes=%s already exist in Target Section." 
                % cdes_found_in_target_section)
        return
    # Copy cdes from first item of source section
    cdes_to_move = [cde for cde in source_section['cdes'][0] if cde['code'] in cde_codes]
    print("******* CDEs to move (from first item only): %s" % cdes_to_move)
    print(" Removing cdes from source section ......")
    # Remove cdes from source section
    updated_source_section = [clean_cdes(cdes_list,cde_codes) for cdes_list in source_section['cdes']]
    source_section['cdes'] = updated_source_section
    print("******* Source section after movement: %s" % source_section)
    print(" Appending cdes to target section ......")
    # Append cdes to target section
    updated_target_section = target_section['cdes'] + cdes_to_move
    target_section['cdes'] = updated_target_section
    print("******* Target section after movement: %s" % target_section)
    print("@@@@@@@ CDE migration completed successfully @@@@@@@")


def clean_cdes(cdes_list,cde_codes):
    cdes_list = [ cde for cde in cdes_list if cde['code'] not in cde_codes]
    return cdes_list
