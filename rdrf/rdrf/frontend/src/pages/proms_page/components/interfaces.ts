import * as Logic from '../logic';

export interface QuestionInterface {
    title: string,
    questions: Logic.ElementList,
    answers?: any,
    stage: number,
    enterData?: any;
   
}

