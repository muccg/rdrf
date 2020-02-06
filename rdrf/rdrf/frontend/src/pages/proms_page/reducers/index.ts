import axios from 'axios';
import { createAction, handleActions } from 'redux-actions';

import { evalElements } from '../logic';

export const goPrevious = createAction("PROMS_PREVIOUS");
export const goNext = createAction("PROMS_NEXT");
export const submitAnswers = createAction("PROMS_SUBMIT");
export const enterData = createAction("PROMS_ENTER_DATA");

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

function submitSurvey(answers: { [index: string]: string }) {
    const patient_token: string = window.proms_config.patient_token;
    const registry_code: string = window.proms_config.registry_code;
    const survey_name: string = window.proms_config.survey_name;
    const surveyEndpoint: string = window.proms_config.survey_endpoint;
    const data = {
        patient_token,
        registry_code,
        survey_name,
        answers
    };
    axios.post(surveyEndpoint, data)
        .then(res => window.location.replace(window.proms_config.completed_page))
        .catch(err => alert(err.toString()));
}

const initialState = {
    stage: 0,
    answers: {},
    questions: evalElements(window.proms_config.questions, { answers: {} }),
    title: '',
}

function isCond(state) {
    const stage = state.stage;
    return state.questions[stage].tag === 'cond';
}

function updateAnswers(action: any, state: any): any {
    // if data entered , update the answers object
    const cdeCode = action.payload.cde;
    const newValue = action.payload.value;
    const oldAnswers = state.answers;
    const newAnswers = { ...oldAnswers };
    newAnswers[cdeCode] = newValue;
    return newAnswers;
}

function clearAnswerOnSwipeBack(state: any): any {
    // clear the answer when move to previous question
    const stage = state.stage;
    const questionCode = state.questions[stage].cde;
    const oldAnswers = state.answers;
    const newAnswers = { ...oldAnswers };
    delete newAnswers[questionCode];
    return newAnswers;
}

function updateConsent(state: any): any {
    const questionCount = state.questions.length;
    const allAnswers = state.answers;
    const questionCode = state.questions[questionCount - 1].cde;
    if (!allAnswers.hasOwnProperty(questionCode)) {
        const oldAnswers = state.answers;
        const newAnswers = { ...oldAnswers };
        newAnswers[questionCode] = false;
        return newAnswers;
    }

    return allAnswers;
}

export const promsPageReducer = handleActions({
    [goPrevious as any]:
        (state, action: any) => ({
            ...state,
            answers: clearAnswerOnSwipeBack(state),
            stage: state.stage - 1,
        }),
    [goNext as any]:
        (state, action: any) => ({
            ...state,
            stage: state.stage + 1,
        }),
    [submitAnswers as any]:
        (state, action: any) => {
            const newState = {
                ...state,
                answers: updateConsent(state),
            };
            submitSurvey(newState.answers);
            return newState;
        },
    [enterData as any]:
        (state, action) => {
            const updatedAnswers = updateAnswers(action, state)
            const newState = {
                ...state,
                answers: updateAnswers(action, state),
                questions: evalElements(window.proms_config.questions, { answers: updatedAnswers }),
            };
            return newState;
        },
}, initialState);
