import * as React from 'react';
import {
    Alert,
    Container,
} from 'reactstrap';


export default props => {
    const ckanURL = (path) => `${window.otu_search_config.ckan_base_url}/${path}`

    return (
        <Container fluid>
            <Alert color="danger" className="text-center">
                <h4 className="alert-heading">Login required</h4>
                <p>
                    Please log into the <a href={ckanURL('user/login')}>Bioplatforms Data Portal</a>, or <a href={ckanURL('user/register')}>request access</a>.
                    If you still cannot access the data after logging in, contact <a href='mailto:help@bioplatforms.com'>support</a>.
                </p>
            </Alert>
        </Container>
    );
}