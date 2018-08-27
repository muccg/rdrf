import axios from 'axios';

function fetchQuestionData(stage) {
  return axios.get(window.proms_config.question_endpoint, {
       params: {
              stage: JSON.stringify(stage),
       },});
}


           
