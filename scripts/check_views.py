'''
TO DO:
    - Further abstract states (maybe find some way of removing reliance on indices)
    - Add comments to provide full information on code
    - Create unit tests for script (view with mixin, view w/out mixin with decorators, no mixin no decorators)
'''

import os
import re
import sys

from os.path import abspath, join


vcheck_states = {
    's': "SEARCH",
    'v': "INVIEW",
}

whitelist = [
    'ClinicianActivationView',
    'CopyrightView',
    'LandingView',
    'PatientsListingView',
    'PromsCompletedPageView',
    'PromsLandingPageView',
    'PromsView',
    'RecaptchaValidator',
    'RegistryListView',
    'RegistryView',
    'RouterView',
    'SurveyEndpoint',
    'UsernameLookup',
]


def get_superclass(class_text):
    super_strings = []
    ret_strings = []
    if re.match(r'^class', class_text) is not None:
        super_strings = re.split(r'^class.+\(|,|\):', class_text)

        for substr in super_strings:
            if substr != "":
                ret_strings.append(substr.strip())
    return ret_strings


def find_view(line_text):
    state_n = 's'
    view_n = ''
    # Check line
    superclass_str = get_superclass(line_text)
    if superclass_str != [] and "View" in superclass_str:
        # Change to "in-view" state if check for mixin is false
        if "LoginRequiredMixin" not in superclass_str:
            state_n = 'v'
            view_n = re.findall(r'class (.+)\(', line_text)
    return state_n, view_n


def validate_view(line_text):
    # more stuff here
    pass


def search_and_check_views(cur_line, all_lines, line_index, cur_state, cur_file, cur_view, f_and_v_list):
    # Change back to normal search once normal indent level is reached (use regex to match no leading whitespace and no comments)
    if re.match(r'^[^\s\#]', cur_line) is not None:
        cur_state = 's'
    # Redefine current state
    new_state = vcheck_states[cur_state]

    # Search until view is found
    if new_state == "SEARCH":
        '''
        # Check line
        superclass_str = get_superclass(cur_line)
        if superclass_str != [] and "View" in superclass_str:
            # Change to "in-view" state if check for mixin is false
            if "LoginRequiredMixin" not in superclass_str:
                cur_state = 'v'
                cur_view = re.findall(r'class (.+)\(', cur_line)
        '''
        cur_state, cur_view = find_view(cur_line)

    # While in "in-view" state, look for get/post methods
    elif new_state == "INVIEW":
        # Check for get/post
        if ("def get(" in cur_line) or ("def post(" in cur_line):
            # Check if get/post has a decorator - if not, add to list
            if ("@method_decorator(login_required)" not in all_lines[line_index - 1]) and \
               ("@login_required" not in all_lines[line_index - 1]):
                # add view class name to list w/regex
                if cur_file not in f_and_v_list:
                    f_and_v_list.update({cur_file: []})
                if cur_view not in f_and_v_list[cur_file]:
                    f_and_v_list[cur_file].append(cur_view)

    return cur_state, cur_view


def remove_whitelisted(insecure_list):
    # Create empty list in which to store files to be removed from the list (ones containing only whitelisted views)
    remove_files = []
    # Loop through files
    for bad_file in insecure_list:
        # Another empty list, this one to remove whitelisted views
        remove_views = []
        # Loop through views
        for bad_view in insecure_list[bad_file]:
            # The view strings are stored in single-element lists for some reason, so we have to access them like so
            # Check if the current view is whitelisted
            if bad_view[0] in whitelist:
                # Populate the list of views to be ignored
                remove_views.append(bad_view)
        # Loop through views to be removed
        for rm_view in remove_views:
            # Remove views
            insecure_list[bad_file].remove(rm_view)
        # Check if there are any remaining insecure views in the file
        if insecure_list[bad_file] == []:
            # Populate list of files to be ignored
            remove_files.append(bad_file)

    # Loop through files to be removed
    for rm_file in remove_files:
        # Remove file
        insecure_list.pop(rm_file)


def check_view_security():
    files_and_views = {}
    dir_name = abspath(sys.argv[1])  # Not the best, but this way only one base directory is read. Perhaps do some error handling if a directory isn't passed in
    
    # Explore base directory and all subdirectories
    for base_dir, sub_dirs, files in os.walk(dir_name):
        # Don't check build folder - removes duplicates
        if "build" not in base_dir:
            # Iterate through file names
            for f_name in files:
                # If file is Python file
                if re.match(r'.+\.py$', f_name) is not None:
                    # Open file and start searching
                    full_f_name = join(base_dir, f_name)
                    f_lines = open(full_f_name).readlines()
                    state = 's'
                    view = ''

                    # Iterate through lines, using enumerate() to grab positional values
                    for index, line_var in enumerate(f_lines):
                        state, view = search_and_check_views(line_var, f_lines, index, state, full_f_name, view, files_and_views)
                        
    remove_whitelisted(files_and_views)

    if len(files_and_views) > 0:
        print("Non-secure views found:")
        for bad_file in files_and_views:
            print(f"File: {bad_file}")
            print("Views:")
            for bad_view in files_and_views[bad_file]:
                print(bad_view)
        sys.exit(1)
    else:
        print("Views secure.")


# Run the primary function if this is being used standalone
if __name__ == "__main__":
    check_view_security()
