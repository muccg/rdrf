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


// conditions

function evalCondition(condition: Condition, state: any) : boolean {
    switch(condition.op) {
	case '=': {
	    const answer = state.answers[condition.cde];
	    return answer === condition.value;
	}
	default:
            return false;
    }
}

function evalElement(e: Element, state: any) {
    switch(e.tag) {
	case 'cde': return e.cde;
	case 'cond': {
	    if (evalCondition(e.cond, state)) {
		return e.cde;
            }
	    else {
		return null;
	    }
	}
	default:
          const _exhaustiveCheck: never = e;
          return _exhaustiveCheck;
    }
}


export function evalElements(elements: Element[], state: any) : string[] {
   const ev = _.partial(evalElement, _, state);
   return elements.map(ev).filter(element => element !== null);
}
