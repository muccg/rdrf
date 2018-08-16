import * as _ from 'lodash';
import axios from 'axios';

import '../interfaces';
import { ckanAuthInfoEnded } from '../reducers/auth';
import { store } from '../init';

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

axios.interceptors.response.use(null, err => {
    if (err.status === 403) {
        store.dispatch(ckanAuthInfoEnded(new Error(err)));
        return;
    }
    return Promise.reject(err);
});

export function ckanAuthInfo() {
    return axios.get(window.otu_search_config.ckan_check_permissions);
}

export function getAmplicons() {
    return axios.get(window.otu_search_config.amplicon_endpoint);
}

export function getContextualDataDefinitions() {
    return axios.get(window.otu_search_config.contextual_endpoint);
}

export function getTaxonomy(selectedAmplicon = {value: ''}, selectedTaxonomies) {
    const taxonomies = completeArray(selectedTaxonomies, 7, {value: ''});

    return axios.get(window.otu_search_config.taxonomy_endpoint, {
        params: {
            amplicon: JSON.stringify(selectedAmplicon),
            selected: JSON.stringify(taxonomies)
        }
    });
}

function doSearch(url, filters, options) {
    let formData = new FormData();
    formData.append('start', (options.page * options.pageSize).toString());
    formData.append('length', options.pageSize);
    formData.append('sorting', JSON.stringify(_.get(options, 'sorted', [])));
    formData.append('columns', JSON.stringify(_.get(options, 'columns', [])));
    formData.append('otu_query', JSON.stringify(filters));

    return axios({
        method: 'post',
        url: url,
        data: formData,
        headers: {
            'Content-Type': 'multipart/form-data',
        }
    });
}

export const executeSearch = _.partial(doSearch, window.otu_search_config.search_endpoint);
export const executeContextualSearch = _.partial(doSearch, window.otu_search_config.required_table_headers_endpoint);

export function executeSampleSitesSearch(filters) {
    let formData = new FormData();
    formData.append('otu_query', JSON.stringify(filters));

    return axios({
        method: 'post',
        url: window.otu_search_config.search_sample_sites_endpoint,
        data: formData,
        headers: {
            'Content-Type': 'multipart/form-data',
        }
    });
}

export function executeSubmitToGalaxy(filters) {
    let formData = new FormData();
    formData.append('query', JSON.stringify(filters));

    return axios({
        method: 'post',
        url: window.otu_search_config.submit_to_galaxy_endpoint,
        data: formData,
        headers: {
            'Content-Type': 'multipart/form-data',
        }
    });
}

export function getGalaxySubmission(submissionId) {
    return axios.get(window.otu_search_config.galaxy_submission_endpoint, {
        params: {
            submission_id: submissionId
        }
    });
}

const makeArray = (length, fillValue) => _.map(Array(length), () => fillValue);
const completeArray = (arr, length, fillValue) => arr.concat(makeArray(length - arr.length, fillValue));

