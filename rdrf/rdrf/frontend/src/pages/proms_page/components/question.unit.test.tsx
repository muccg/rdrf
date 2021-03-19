// Question.unit.test.tsx

import * as React from 'react';
import ReactDOM from 'react-dom';
import Question from './question';
import * as Logic from '../logic';

//var elList = Logic.evalElements([{"cde": "doy"}], {});
var newQuestion = <Question /> //title="test" />; //questions={elList}/>;

describe('Question', () => {
    it('is defined', () => {
        expect(newQuestion).toBeDefined();
    });
    it('has properties', () => {
        expect(newQuestion).toHaveProperty('props')
    });
    // Etc. etc.
    // Check Jest API for more methods
});