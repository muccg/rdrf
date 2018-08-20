import { createActions, handleActions, handleAction, combineActions } from 'redux-actions';

const {
    goPrevious,
    goNext,
} = createActions('PROMS_PREVIOUS','PROMS_NEXT');


const pageReducer = handleActions({

}, []);

export default pageReducer;

