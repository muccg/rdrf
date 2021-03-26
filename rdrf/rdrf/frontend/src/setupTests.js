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