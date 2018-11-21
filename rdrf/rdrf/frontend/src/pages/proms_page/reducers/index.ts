import { createAction, handleActions } from 'redux-actions';

export const goPrevious = createAction("PROMS_PREVIOUS");
export const goNext = createAction("PROMS_NEXT");
export const submitAnswers = createAction("PROMS_SUBMIT");
export const enterData = createAction("PROMS_ENTER_DATA");

import { evalElements } from '../logic';
import axios from 'axios';

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

function submitSurvey(answers: { [index: string]: string }) {
    let patientToken: string = window.proms_config.patient_token;
    let registryCode: string = window.proms_config.registry_code;
    let surveyName: string = window.proms_config.survey_name;
    let surveyEndpoint: string = window.proms_config.survey_endpoint;
    let data = {
        patient_token: patientToken,
        registry_code: registryCode,
        survey_name: surveyName,
        answers: answers
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
    return state.questions[stage].tag == 'cond';
}


function updateAnswers(action: any, state: any): any {
    // if data entered , update the answers object
    let cdeCode = action.payload.cde;
    let newValue = action.payload.value;
    let oldAnswers = state.answers;
    var newAnswers = { ...oldAnswers };
    newAnswers[cdeCode] = newValue;
    return newAnswers;
}

function clearAnswerOnSwipeBack(state: any): any {
    // clear the answer when swipe to previous question
    const stage = state.stage;
    let questionCode = state.questions[stage].cde;
    let oldAnswers = state.answers;
    let newAnswers = { ...oldAnswers };
    delete newAnswers[questionCode];
    return newAnswers;
}

function updateConsent(state: any): any {
    let questionCount = state.questions.length;
    console.log("No of Questions " + questionCount);
    let oldAnswers = state.answers;
    var answerCount = Object.keys(oldAnswers).length;
    console.log("No of Answers " + answerCount);
    if (questionCount > answerCount) {
        let questionCode = state.questions[questionCount - 1].cde;
        let oldAnswers = state.answers;
        let newAnswers = { ...oldAnswers };
        newAnswers[questionCode] = false;
        return newAnswers;
    }

    return oldAnswers;
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
            console.log("submitting answers");
            let newState = {
                ...state,
                answers: updateConsent(state),
            };
            submitSurvey(newState.answers);
            return newState;
        },
    [enterData as any]:
        (state, action) => {
            console.log("enterData action received");
            console.log("action = " + action.toString());
            console.log("answers before update = " + state.answers.toString());
            
            let updatedAnswers = updateAnswers(action, state)
            console.log("updated answers = " + updatedAnswers.toString());
            let newState = {
                ...state,
                answers: updateAnswers(action, state),
                questions: evalElements(window.proms_config.questions, { answers: updatedAnswers }),
            };
            console.log("newState = " + newState.toString());
            return newState;
        },
}, initialState);
