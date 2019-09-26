import axios from 'axios';

function fetchSurvey(registryCode, surveyName) {
  return axios.get(window.proms_config.survey_endpoint, {
    params: {
      survey_id: JSON.stringify(registryCode, surveyName),
    },
  });
}



