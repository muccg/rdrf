import yaml
import sys
import os

"""
Looks for differences in
    Common Data Elements and
    Survey Questions
in two registry definition yaml files.
"""


def get_dict_of_items(yaml_data, list_to_compare, identifier):
    return {item[identifier]: [attr + ": " + str(item[attr]) for attr in item] for item in yaml_data[list_to_compare]}


def compare_dicts(dict1, dict2, result_file):
    diff_count = 0
    for key in list(set(list(dict1.keys()) + list(dict2.keys()))):
        if key not in dict1:
            result_file.write("%s,%s,%s\n" % (key, "Not found", " "))
            diff_count += 1
        elif key not in dict2:
            result_file.write("%s,%s,%s\n" % (key, " ", "Not found"))
            diff_count += 1
        elif dict1[key] or dict2[key]:
            for i in range(len(dict1[key]) or len(dict2[key])):
                if dict1[key][i] != dict2[key][i]:
                    result_file.write("%s,%s,%s\n" % (key, dict1[key][i], dict2[key][i]))
                    diff_count += 1
    if not diff_count:
        result_file.write("No difference found\n")


def get_survey(surveys, name):
    for survey in surveys:
        if survey["name"] == name:
            return survey


yaml_file_1 = sys.argv[1]
yaml_file_2 = sys.argv[2]

out_path = os.path.dirname(os.path.abspath(__file__))
out_file = os.path.join(out_path, "differences.csv")

with open(yaml_file_1) as yf1, open(yaml_file_2) as yf2, open(out_file, 'w+') as result_file:
    data1 = yaml.load(yf1, yaml.SafeLoader)
    data2 = yaml.load(yf2, yaml.SafeLoader)

    result_file.write("files: %s %s\n" % (yaml_file_1, yaml_file_2))
    result_file.write("registry definition: %s\n" % (data1["code"]))
    result_file.write("versions: %s %s\n" % (data1["REGISTRY_VERSION"], data2["REGISTRY_VERSION"]))

    # Compare CDEs ############################################################
    result_file.write("\nCommon Data Elements::\n")

    dict1 = get_dict_of_items(data1, "cdes", "code")
    dict2 = get_dict_of_items(data2, "cdes", "code")
    compare_dicts(dict1, dict2, result_file)

    # Compare Survey Questions ##################################################
    result_file.write("\nSurvey Questions::\n")

    surveys1 = data1["surveys"]
    surveys2 = data2["surveys"]

    for survey in surveys1:
        survey_name = survey["name"]
        result_file.write("\nIn Survey: %s\n" % survey_name)

        dict1 = get_dict_of_items(survey, "questions", "cde")
        dict2 = get_dict_of_items(get_survey(surveys2, survey_name), "questions", "cde")
        compare_dicts(dict1, dict2, result_file)
