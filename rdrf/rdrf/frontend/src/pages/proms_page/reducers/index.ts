import { createAction, handleActions, handleAction, combineActions } from 'redux-actions';

const PREVIOUS  = createAction("PROMS_PREVIOUS");
const NEXT = createAction("PROMS_NEXT");

const initialState = {
    stage: 0,
}

export const promsPageReducer = handleActions({
    [PREVIOUS as any]:
    (state, action: any) => ({
	...state,
	stage: state.stage - 1,
    }),
    [NEXT as any]:
    (state, action: any) => ({
	...state,
	stage: state.stage + 1,
    }),
}, initialState);
