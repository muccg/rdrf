// Question.unit.test.tsx

import * as React from 'react';
import ReactDOM from 'react-dom';
import Question from './question';
import * as Logic from '../logic';

const dummyQuestions1 = [
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
        "tag": "range",
        "options": [
          {
            "code": "answer1",
            "text": "Anwser 1"
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
      "spec": null
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
        "tag": "range",
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
];
// var elList = Logic.evalElements([{"cde": "doy"}], {});
// var newQuestion = <Question title="test" questions={elList}/>;

describe('An empty Question', () => {
    const newQuestion = <Question />
    it('is defined', () => {
        expect(newQuestion).toBeDefined();
    });
    it('has properties', () => {
        expect(newQuestion).toHaveProperty('props');
    });
    it('does not have a title', () => {
        expect(newQuestion.props).not.toHaveProperty('title')
    });
    it('does not have questions', () => {
        expect(newQuestion.props).not.toHaveProperty('questions');
    });
    // Etc. etc.
    // Check Jest API for more methods
});

/* To do
describe('A Question with dummy data', () => {
    var elList = Logic.evalElements(dummy_questions_1, {});
    // var newQuestion = <Question title="test" questions={elList}/>;
});
*/