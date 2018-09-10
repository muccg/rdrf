import { createAction, handleActions } from 'redux-actions';

export const goPrevious  = createAction("PROMS_PREVIOUS");
export const goNext = createAction("PROMS_NEXT");
export const submit = createAction("PROMS_SUBMIT");

export const enterData = createAction("PROMS_ENTER_DATA");


import { evalElements } from '../logic';


const initialState = {
    stage: 0,
    answers: {},
    questions: evalElements(window.proms_config.questions, {answers: {}}),
    title: '',
}

function isCond(state) {
    const stage = state.stage;
    return state.questions[stage].tag == 'cond';
}


function updateAnswers(action: any, state: any) : any {
    // if data entered , update the answers object
    let cdeCode = action.payload.cde;
    let newValue = action.payload.value;
    let oldAnswers = state.answers;
    let newAnswers = {...oldAnswers,
		      cdeCode: newValue,
		     };
    return newAnswers;
}

export const promsPageReducer = handleActions({
    [goPrevious as any]:
    (state, action: any) => ({
	...state,
	stage: state.stage - 1,
    }),
    [goNext as any]:
    (state, action: any) => ({
	...state,
	stage: state.stage + 1,
    }),
    [enterData as any]:
    (state, action) => {
	let updatedAnswers = updateAnswers(action, state)
	let newState = {
	    ...state,
	    answers: updateAnswers(action, state),
	    questions: evalElements(window.proms_config.questions,{answers: updatedAnswers}),
	};
	return newState;
    },	
}, initialState);
