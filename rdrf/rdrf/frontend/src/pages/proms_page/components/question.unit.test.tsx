// Question.unit.test.tsx

import * as React from 'react';
import ReactDOM from 'react-dom';
import Question from './question';
import * as Logic from '../logic';

describe('An empty Question', () => {
    // const newQuestion = <Question />
    const newQuestion = new Question.WrappedComponent({});
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
    it('throws an exception when entering data', () => {
        expect(() => {
            newQuestion.props.enterData("cde1", "yes", true);
        }).toThrow();
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