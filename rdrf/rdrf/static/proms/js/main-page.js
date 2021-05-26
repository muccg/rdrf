function addPromsConfigToWindow(questions, patient_token, registry_code, survey_endpoint, survey_name, completed_page) {
    var questions = JSON.parse(questions);
    window.proms_config = {
        patient_token: patient_token,
        questions: questions,
        registry_code: registry_code,
        survey_endpoint: survey_endpoint,
        survey_name: survey_name,
        completed_page: completed_page
    };
}


