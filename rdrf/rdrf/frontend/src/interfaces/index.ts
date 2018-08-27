export interface PromsConfig {
     question_endpoint: string,
 }


declare global {
    interface Window  {
	proms_config: PromsConfig,
    }
}


