import * as _ from 'lodash';

interface EqualsCondition {
    op: '=',
    cde: string,
    value: any,
}

interface OrCondition {
    op: 'or',
    cde: string,
    value: any,
}

// maybe this is enough
type Condition = EqualsCondition | OrCondition;

// Elements of workflow
// I tried to make UnconditionalElement just a string but got type errors
interface Option {
    code: string,
    text: string,
}

interface RangeDatatype {
    tag: 'range',
    options: [Option],
    allow_multiple: boolean,
}

interface IntegerDatatype {
    tag: 'integer',
    max: number,
    min: number,
}

type Datatype = RangeDatatype | IntegerDatatype;

interface UnconditionalElement {
    tag: 'cde',
    cde: string,
    title: string,
    instructions: string,
    spec: Datatype,
    survey_question_instruction: string,
    copyright_text: string,
    source: string,
    datatype: string
}

interface ConditionalElement {
    tag: 'cond',
    cond: Condition,
    cde: string,
    title: string,
    instructions: string,
    spec: Datatype,
    survey_question_instruction: string,
    copyright_text: string,
    source: string,
    datatype: string
}

type Element = UnconditionalElement | ConditionalElement;

export type ElementList = [Element];

function evalCondition(cond: Condition, state: any): boolean {
    // Evaluates a conditional element in the current state
    // We only show applicable questions - i.e. those
    // which evaluate to true
    if (state.answers.hasOwnProperty(cond.cde)) {
        const answer = state.answers[cond.cde];
        switch (cond.op) {
            case '=':
                return answer === cond.value;
	    case 'or':
		return cond.value.indexOf(answer) > -1;
            default:
                return false; // extend this later
        }
    }
    else {
        return false;
    }
}


function evalElement(el: Element, state: any): boolean {
    switch (el.tag) {
        case 'cde':
            // Unconditional elements are always shown
            return true;
        case 'cond':
            // conditional elements depend their associated
            // condition being true
            return evalCondition(el.cond, state);
        default:
            return false;
    }
}


export function evalElements(elements: Element[], state: any): Element[] {
    // The questions to show at any time are those whose preconditions
    // are fulfilled
    return elements.filter(el => evalElement(el, state));
}

