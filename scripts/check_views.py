import os, re, sys

from os.path import abspath, join


vcheck_states = {
    's' : "SEARCH",
    'v' : "INVIEW",
}


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

                    # Iterate through lines, using enumerate() to grab positional values
                    for index, line_var in enumerate(f_lines):
                        # Change back to normal search once normal indent level is reached (use regex to match no leading whitespace and no comments)
                        if re.match(r'^[^\s\#]', line_var) is not None:
                            state = 's'
                        # Redefine current state
                        cur_state = vcheck_states[state]

                        # Search until view is found
                        if cur_state == "SEARCH":
                            # Check line
                            if re.match(r'^class.+\((?:.+, )?View\)', line_var) is not None:
                                # Change to "in-view" state if check for mixin is false
                                if "LoginRequiredMixin" not in line_var:
                                    state = 'v'
                                    cur_view = re.findall(r'class (.+)\(', line_var)

                        # While in "in-view" state, look for get/post methods
                        elif cur_state == "INVIEW":
                            # Check for get/post
                            if ("def get(" in line_var) or ("def post(" in line_var):
                                # Check if get/post has a decorator - if not, add to list
                                if ("@method_decorator(login_required)" not in f_lines[index - 1]) and ("@login_required" not in f_lines[index - 1]):
                                    # add view class name to list w/regex
                                    if full_f_name not in files_and_views:
                                        files_and_views.update({full_f_name : []})
                                    if cur_view not in files_and_views[full_f_name]:
                                        files_and_views[full_f_name].append(cur_view)

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
