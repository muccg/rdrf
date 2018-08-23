import { createAction, handleActions, handleAction, combineActions } from 'redux-actions';

export const goPrevious  = createAction("PROMS_PREVIOUS");
export const goNext = createAction("PROMS_NEXT");

const initialState = {
    stage: 0,
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
