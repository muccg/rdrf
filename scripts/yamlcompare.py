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
    return {item[identifier]: [[attr, str(item[attr])] for attr in item] for item in yaml_data[list_to_compare]}


def get_question_string(question, cde_dict):
    cde_code = question[0][1]
    cde = cde_dict[cde_code]
    for attr in cde:
        if attr[0] == "name":
            return attr[1]


def compare_dicts(category, dict1, dict2, result_file, cde_dict=None, survey_name=None):
    for key in sorted(list(set(list(dict1.keys()) + list(dict2.keys())))):
        if key not in dict1:
            result_file.write("%s,%s,%s,%s\n" % (category, key, "Not found", " "))
        elif key not in dict2:
            result_file.write("%s,%s,%s,%s\n" % (category, key, " ", "Not found"))
        elif dict1[key] or dict2[key]:
            for i in range(len(dict1[key]) or len(dict2[key])):
                if dict1[key][i] != dict2[key][i]:
                    if category == "Survey Question":
                        question = survey_name + " > " + key + " (" + get_question_string(dict1[key], cde_dict) + ")"
                        result_file.write("%s,%s,%s,%s,%s\n" % (category, question, dict1[key][i][0],
                                                                dict1[key][i][1], dict2[key][i][1]))
                    else:
                        result_file.write("%s,%s,%s,%s,%s\n" % (category, key,
                                                                dict1[key][i][0], dict1[key][i][1].replace("\n", " "),
                                                                dict2[key][i][1].replace("\n", " ")))


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

    cde_dict1 = get_dict_of_items(data1, "cdes", "code")
    cde_dict2 = get_dict_of_items(data2, "cdes", "code")
    compare_dicts("CDE", cde_dict1, cde_dict2, result_file)

    surveys1 = data1["surveys"]
    surveys2 = data2["surveys"]

    for survey in surveys1:
        q_dict1 = get_dict_of_items(survey, "questions", "cde")
        q_dict2 = get_dict_of_items(get_survey(surveys2, survey["name"]), "questions", "cde")
        compare_dicts("Survey Question", q_dict1, q_dict2, result_file, cde_dict=cde_dict1, survey_name=survey["name"])
