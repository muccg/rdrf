import { createAction, handleActions, handleAction, combineActions } from 'redux-actions';

const PREVIOUS  = createAction("PROMS_PREVIOUS");
const NEXT = createAction("PROMS_NEXT");

const initialState = {
    stage: 0
}


const pageReducer = handleActions({
    PREVIOUS:
    (state, action: any) => ({
	...state,
	state.stage = state.stage - 1
    }),
    NEXT:
    (state, action: any) => ({
	...state,
	state.stage = state.stage + 1
    }),
    
	
}, initialState);

export default pageReducer;

