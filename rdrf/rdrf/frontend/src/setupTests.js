window.proms_config = {
    patient_token: "123456789",
    questions: [
      {
        "tag": "cde",
        "cde": "registryQ1",
        "datatype": "range",
        "instructions": "",
        "title": "Question 1 - title",
        "survey_question_instruction": "",
        "copyright_text": "",
        "source": "",
        "spec": {
          "ui": "range",
          "options": [
            {
              "code": "answer1",
              "text": "Answer 1"
            },
            {
              "code": "answer2",
              "text": "Answer 2"
            }
          ],
          "allow_multiple": false
        }
      },
      {
        "tag": "cde",
        "cde": "registryQ2",
        "datatype": "string",
        "instructions": "",
        "title": "Question 2 - title",
        "survey_question_instruction": "",
        "copyright_text": "",
        "source": "",
        "spec": {
          "ui": "text"
        }
      },
      {
        "tag": "cond",
        "cond": {
          "op": "or",
          "cde": "registryQ1",
          "value": ["answer1", "answer2"]
        },
        "cde": "registryQ3",
        "title": "Question 3 - title",
        "instructions": "This question requires other questions to be answered first.",
        "spec": {
          "ui": "range",
          "options": [
            {
              "code": "good_answer",
              "text": "Good"
            },
            {
              "code": "not_good_answer",
              "text": "Not so good"
            },
            {
              "code": "bad_answer",
              "text": "Bad"
            }
          ],
          "allow_multiple": false
        },
        "survey_question_instruction": "How are you?",
        "copyright_text": "",
        "source": "",
        "datatype": "range"
      },
      {
        "tag": "cond",
        "cond": {
          "op": "=",
          "cde": "registryQ3",
          "value": "bad_answer"
        },
        "cde": "registryQ4",
        "title": "Question 4 - title",
        "instructions": "Another preconditional question",
        "spec": {
          "ui": "multi_select",
          "options": [
            {
              "code": "work_answer",
              "text": "Work is stressful"
            },
            {
              "code": "friends_answer",
              "text": "Can't see my friends"
            },
            {
              "code": "react_answer",
              "text": "React is difficult"
            },
            {
              "code": "day_answer",
              "text": "Just a bad day"
            }
          ],
          "allow_multiple": true
        },
        "survey_question_instruction": "Why do you feel bad?",
        "copyright_text": "",
        "source": "",
        "datatype": "range"
      },
      {
        "tag": "cond",
        "cond": {
          "op": "contains",
          "cde": "registryQ4",
          "value": "react_answer"
        },
        "cde": "registryQ5",
        "title": "Question 5 - title",
        "instructions": "Given your work with React:",
        "spec": {
          "ui": "multi_select",
          "options": [
            {
              "code": "hard_to_read",
              "text": "It's hard to read"
            },
            {
              "code": "too_many_deps",
              "text": "It has too many dependencies"
            },
            {
              "code": "by_fb",
              "text": "It's made by Facebook"
            },
            {
              "code": "zero_understanding",
              "text": "I don't understand it"
            }
          ],
          "allow_multiple": true
        },
        "survey_question_instruction": "What do you find difficult with React?",
        "copyright_text": "",
        "source": "",
        "datatype": "range"
      },
      {
        "tag": "cond",
        "cond": {
          "op": "intersection",
          "cde": "registryQ5",
          "value": ["too_many_deps", "by_fb"]
        },
        "cde": "registryQ6",
        "title": "Question 6 - title",
        "instructions": "As some of your difficulties can't be addressed:",
        "spec": {
          "ui": "text"
        },
        "survey_question_instruction": "Use this space to vent your frustrations.",
        "copyright_text": "",
        "source": "",
        "datatype": "text"
      },
      {
        "tag": "cond",
        "cond": {
          "op": "=",
          "cde": "registryQ6",
          "value": "typetest"
        },
        "cde": "registryQ7",
        "title": "Question 7 - title",
        "instructions": "",
        "spec": {
          "ui": "integer-normal",
          "params": {
            "type": "text",
            "max": "1000",
            "min": "0"
          }
        },
        "survey_question_instruction": "",
        "copyright_text": "",
        "source": "",
        "datatype": "integer"
      },
      {
        "tag": "cond",
        "cond": {
          "op": "=",
          "cde": "registryQ6",
          "value": "typetest"
        },
        "cde": "registryQ8",
        "title": "Question 8 - title",
        "instructions": "",
        "spec": {
          "ui": "integer-slider",
          "max": 10,
          "min": 0,
          "params": {
            "max": "10",
            "min": "1"
          },
          "widget_spec": {
            "widget_name": "slider",
            "min_label": "The worst",
            "max_label": "The best",
            "box_label": "On a scale of 1 to 10:"
          }
        },
        "survey_question_instruction": "",
        "copyright_text": "",
        "source": "",
        "datatype": "integer"
      },
      {
        "tag": "cond",
        "cond": {
          "op": "=",
          "cde": "registryQ6",
          "value": "typetest"
        },
        "cde": "registryQ9",
        "title": "Question 9 - title",
        "instructions": "",
        "spec": {
          "ui": "float",
          "params": {
            "max": "1000",
            "min": "0"
          }
        },
        "survey_question_instruction": "",
        "copyright_text": "",
        "source": "",
        "datatype": "float"
      },
      {
        "tag": "cond",
        "cond": {
          "op": "=",
          "cde": "registryQ6",
          "value": "typetest"
        },
        "cde": "registryQ10",
        "title": "Question 10 - title",
        "instructions": "",
        "spec": {
          "ui": "date"
        },
        "survey_question_instruction": "",
        "copyright_text": "",
        "source": "",
        "datatype": "date"
      },
      {
        "tag": "cond",
        "cond": {
          "op": "=",
          "cde": "registryQ6",
          "value": "typetest"
        },
        "cde": "registryQ11",
        "title": "Question 11 - title",
        "instructions": "",
        "spec": {
          "ui": "consent"
        },
        "survey_question_instruction": "",
        "copyright_text": "",
        "source": ""
      },
      {
        "tag": "cond",
        "cond": {
          "op": "=",
          "cde": "registryQ6",
          "value": "typetest"
        },
        "cde": "registryQ12",
        "title": "Question 12 - title",
        "instructions": "",
        "spec": {
          "ui": "range",
          "options": [
            {
              "code": "answer1",
              "text": "First answer"
            },
            {
              "code": "answer2",
              "text": "Second answer"
            },
            {
              "code": "answer3",
              "text": "Third answer"
            }
          ],
          "allow_multiple": false
        },
        "survey_question_instruction": "",
        "copyright_text": "",
        "source": "",
        "datatype": "range"
      },
      {
        "tag": "cde",
        "cde": "PROMSConsent",
        "datatype": "range",
        "instructions": "Thank you for completing this survey.  We realise that the information you have provided is personal and sensitive and so your confidentiality will be protected at all times. Only your doctor will have access to your individual information. Any use of your information for research purposes will only be in a non- identifiable, combined format.",
        "title": "Consent",
        "survey_question_instruction": "",
        "copyright_text": "",
        "source": "",
        "spec": {
          "ui": "range",
          "options": [
            {
              "code": "fh_yes_no_yes",
              "text": "Yes"
            },
            {
              "code": "fh_yes_no_no",
              "text": "No"
            }
          ],
          "allow_multiple": false
        }
      }
    ],
    survey_endpoint: "",
    survey_name: "",
    registry_code: "",
    csrf_token: "",
    completed_page: ""
};