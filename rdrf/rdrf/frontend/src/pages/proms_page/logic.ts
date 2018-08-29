import * as _ from 'lodash';

interface EqualsCondition {
    op: '=',
    cde: string,
    value: any
}

// maybe this is enough
type Condition = EqualsCondition;

// Elements of workflow
interface UnconditionalElement {
    tag: 'cde',
    cde: string,
}

interface ConditionalElement {
    tag: 'cond',
    cond: Condition,
    cde: string,
}

type Element = UnconditionalElement | ConditionalElement;

type ElementList = [Element];

type CDEList = [string]; // list of cde codes


// conditions



function evalCondition(condition: Condition, state: any) : boolean {
    switch(condition.op) {
	case '=': {
	    const answer = state.answers[condition.cde];
	    return answer === condition.value;
	}
	default: {
	    return false;
	}
    }
}

function evalElement(e: Element, state: any) {
    switch(e.tag) {
	case 'cde': {
	    return e.cde;
	}
	    
	case 'cond': {
	    if (evalCondition(e.cond, state)) {
		return e.cde;
            }
	    else {
		return null;
	    }
	}
	    
    }
}



export function evalElements(elements: Element[], state: any) : string[] {
   const ev = _.partial(evalElement, _, state);
    return elements.map(ev).filter(element => element !== null);
}



const currentState  = {answers: { hadSurgery: 'no', height: 82.6 }};


		 
const workflow: Element[] = [ {tag: "cde", cde: "height"},
			      {tag: "cond",
			       cond: {op: "=", cde: "hadSurgery", value: "yes"},
			       cde: "fred"}];




console.log(evalElements(workflow, currentState));
