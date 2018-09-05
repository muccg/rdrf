export interface PromsConfig {
     survey_endpoint: string,
 }


declare global {
    interface Window  {
	proms_config: PromsConfig,
    }
}


