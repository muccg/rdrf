import * as React from 'react';
import {
    Alert,
    Container,
} from 'reactstrap';


export default props => {
    const ckanURL = (path) => `${window.otu_search_config.ckan_base_url}/${path}`

    return (
        <Container fluid>
            <Alert color="warning" className="text-center">
                <h4 className="alert-heading">Login Required</h4>
                <p>
                    Please stand by while we're checking your permissions to the Bioplatforms Data Portal.
                    If you cannot access the application, contact <a href='mailto:help@bioplatforms.com'>support</a>.
                </p>
            </Alert>
        </Container>
    );
}

