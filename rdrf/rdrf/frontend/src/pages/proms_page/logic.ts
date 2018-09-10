import * as _ from 'lodash';

interface EqualsCondition {
    op: '=',
    cde: string,
    value: any,
}

// maybe this is enough
type Condition = EqualsCondition;

// Elements of workflow
// I tried to make UnconditionalElement just a string but got type errors
interface Option {
    code: string,
    text: string,
}

interface UnconditionalElement  {
    tag: 'cde',
    cde: string,
    title: string,
    options: [Option],
}

interface ConditionalElement {
    tag: 'cond',
    cond: Condition,
    cde: string,
    title: string,
    options: [Option],
}

type Element = UnconditionalElement | ConditionalElement;

export type ElementList = [Element];

function evalCondition(cond: Condition, state: any): boolean {
    if (state.answers.hasOwnProperty(cond.cde) {
	let answer = state.answers[cond.cde];
	switch (cond.op) {
	    case '=':
		return answer == cond.value;
            default:
		return false; // extend this later
	}
    }
    else {
	return false;
    }
}
    

function evalElement(el:Element, state: any): boolean {
    switch(el.tag) {
	case 'cde':
	    return true;
	case 'cond':
	    return evalCondition(el.cond, state);
	case default:
	    return false;
    }
}


export function evalElements(elements: Element[], state): Element[] {
    return elements.filter(el => evalElement(el, state));
}
 
