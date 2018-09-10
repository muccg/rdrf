import * as Logic from '../pages/proms_page/logic';

export interface PromsConfig {
    patient_token: string,
    questions: Logic.ElementList,
    survey_endpoint: string,
    survey_name: string,
    registry_code: string,
    csrf_token: string,
    completed_page: string,
}

declare global {
    interface Window  {
	proms_config: PromsConfig,
    }
}


