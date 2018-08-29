import { createAction, handleActions, handleAction, combineActions } from 'redux-actions';

export const goPrevious  = createAction("PROMS_PREVIOUS");
export const goNext = createAction("PROMS_NEXT");


// need to work out if this is necessary
export const fetchQuestionStart = createAction("PROMS_FETCH_QUESTION_START")
export const fetchQuestionData = createAction("PROMS_FETCH_QUESTION");
export const fetchQuestionFinish = createAction("PROMS_FETCH_QUESTION_FINISH")

const dummyInitialState = {
    stage: 0,
    questions: [ 
	{text: "Pain", options: [{ value: "1", text: "Low"},
                                 { value: "2", text: "Medium"},
                                 { value: "3", text: "High"}]},
	
	{text: "Weight", options: [{ value: "A", text: "Small"},
                                 { value: "B", text: "Medium"},
                                   { value: "C", text: "Heavy"}]}],
}
const initialState = {
    stage: 0,
    answers: {},
    questions: [],
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
