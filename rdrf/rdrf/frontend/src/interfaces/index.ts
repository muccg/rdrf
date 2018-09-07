import * as Logic from '../pages/proms_page/logic';

export interface PromsConfig {
    patient_token: string,
    questions: Logic.ElementList,
    survey_endpoint: string,
}

declare global {
    interface Window  {
	proms_config: PromsConfig,
    }
}


