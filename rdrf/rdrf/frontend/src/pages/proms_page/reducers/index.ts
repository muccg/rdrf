import { createAction, handleActions } from 'redux-actions';

import { 

export const goPrevious  = createAction("PROMS_PREVIOUS");
export const goNext = createAction("PROMS_NEXT");
export const skip = createAction("PROMS_SKIP");
export const submit = createAction("PROMS_SUBMIT");

const initialState = {
    stage: 0,
    answers: {},
    questions: window.proms_config.questions,
    title: '',
}

function isCond(state) {
    const stage = state.stage;
    return state.questions[stage].tag == 'cond';
}

function goNext(state) {
    const stage = state.stage;
    const numQuestions = state.questions.length;
    const atEnd = stage == numQuestions - 1;
    if (atEnd) {
	return state;
    }
    else {
	const nextQuestion = 
    

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
}, initialState);
