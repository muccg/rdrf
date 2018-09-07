import { createAction, handleActions } from 'redux-actions';

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

function isCond(stage, state) {
    return stage.questions[stage].tag == 'cond';
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
}, initialState);
