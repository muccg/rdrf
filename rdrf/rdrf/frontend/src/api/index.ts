import axios from 'axios';

function fetchSurvey(surveyId) {
  return axios.get(window.proms_config.survey_endpoint, {
       params: {
           survey_id: JSON.stringify(surveyId),
       },});
}


           
