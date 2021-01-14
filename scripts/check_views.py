'''
TO DO:
    - Further abstract states (maybe find some way of removing reliance
      on indices)
    - Add comments to provide full information on code
    - Create unit tests for script (view with mixin, view w/out mixin
      with decorators, no mixin no decorators)
'''

import os
import re
import sys

from os.path import abspath, join


check_decorator_strings = [
    '@method_decorator(login_required)',
    '@login_required',
]

check_method_strings = [
    'def get(',
    'def post(',
]

ignore_dirs = set([
    'build',
])

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


def get_lines(file_name, file_dir):
    full_file = join(file_dir, file_name)
    lines = open(full_file).readlines()
    return lines, full_file


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
            view_n = re.findall(r'class (.+)\(', line_text)[0]
    return state_n, view_n


def validate_view(line_text, v_lines, v_index):
    has_failed = False
    # Check for get/post
    if any(met_str in line_text for met_str in check_method_strings):
        # Check if get/post has a decorator - if not, add to list
        if not any(dec_str in v_lines[v_index - 1] for
                   dec_str in check_decorator_strings):
            has_failed = True
    return has_failed


def search_and_check_views(cur_line, all_lines, line_index,
                           cur_state, cur_view):
    view_failed = False
    # Change back to normal search once normal indent level is reached
    # (use regex to match no leading whitespace and no comments)
    if re.match(r'^[^\s\#]', cur_line) is not None:
        cur_state = 's'
    # Redefine current state
    new_state = vcheck_states[cur_state]

    # Search until view is found
    if new_state == "SEARCH":
        cur_state, cur_view = find_view(cur_line)

    # While in "in-view" state, look for get/post methods
    elif new_state == "INVIEW":
        view_failed = validate_view(cur_line, all_lines, line_index)

    return view_failed, cur_state, cur_view


def remove_whitelisted(insecure_dict):
    remove_files = []

    for bad_file, bad_views in insecure_dict.items():
        remove_views = []
        for bad_view in bad_views:
            if bad_view in whitelist:
                remove_views.append(bad_view)
        for rm_view in remove_views:
            insecure_dict[bad_file].remove(rm_view)
        if insecure_dict[bad_file] == []:
            remove_files.append(bad_file)

    for rm_file in remove_files:
        insecure_dict.pop(rm_file)


def show_bad_views(file_view_dict):
    if len(file_view_dict) > 0:
        print("Non-secure views found:")
        for bad_file, bad_views in file_view_dict.items():
            print(f"File: {bad_file}")
            print("Views:")
            for bad_view in bad_views:
                print(bad_view)
        sys.exit(1)
    else:
        print("Views secure.")


def check_view_security():
    files_and_views = {}
    # Not the best, but this way only one base directory is read.
    # Perhaps do some error handling if a directory isn't passed in
    dir_name = abspath(sys.argv[1])

    for base_dir, sub_dirs, files in os.walk(dir_name, topdown=True):
        # Don't check certain folders - removes duplicates
        sub_dirs[:] = [s_dir for s_dir in sub_dirs if
                       s_dir not in ignore_dirs]
        for f_name in files:
            if re.match(r'.+\.py$', f_name) is not None:
                f_lines, full_f_name = get_lines(f_name, base_dir)
                state = 's'
                view = ''
                view_list = []

                for index, line_var in enumerate(f_lines):
                    weak_view, state, view = search_and_check_views(
                        line_var, f_lines, index, state, view
                        )

                    if weak_view:
                        if view not in view_list:
                            view_list.append(view)

                if view_list != []:
                    files_and_views.update({full_f_name: view_list})

    remove_whitelisted(files_and_views)
    show_bad_views(files_and_views)


# Run the primary function if this is being used standalone
if __name__ == "__main__":
    check_view_security()
