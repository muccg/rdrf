// Question.unit.test.tsx

import * as React from 'react';
import ReactDOM from 'react-dom';
import Question from './question';
import * as Logic from '../logic';

//var elList = Logic.evalElements([{"cde": "doy"}], {});
//var newQuestion = <Question /> //title="test" />; //questions={elList}/>;

describe('An empty Question', () => {
    let newQuestion = <Question />
    it('is defined', () => {
        expect(newQuestion).toBeDefined();
    });
    it('has properties', () => {
        expect(newQuestion).toHaveProperty('props');
    });
    it('does not have questions', () => {
        expect(newQuestion.props).not.toHaveProperty('questions');
    });
    // Etc. etc.
    // Check Jest API for more methods
});