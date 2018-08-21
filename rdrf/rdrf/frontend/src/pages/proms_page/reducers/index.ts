import { createAction, handleActions, handleAction, combineActions } from 'redux-actions';

const PREVIOUS  = createAction("PROMS_PREVIOUS");
const NEXT = createAction("PROMS_NEXT");

const pageReducer = handleActions({
    PREVIOUS:
    (state, action: any) => ({
	...state,
    }),
    NEXT:
    (state, action: any) => ({
	...state,
    }),
    
	
}, []);

export default pageReducer;

