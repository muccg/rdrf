import * as _ from 'lodash';
import * as React from 'react';

export default props => {
    const logoPNG = (name) => _.join([window.otu_search_config.static_base_url, 'bpa-logos', name], '/');
    return (
        <footer className="site-footer space-above">
            <div className="site-footer-links container-fluid">
                <a href="http://www.bioplatforms.com">Operated by Bioplatforms Australia</a>
                <a href="https://github.com/muccg/bpaotu">Source Code</a>
                <a href="mailto:help@bioplatforms.com">Contact</a>
            </div>
            <div className="site-footer-logo container-fluid">
                <span>
                    <a href="https://www.bioplatforms.com">
                        <img className="footer-logos" src={ logoPNG('bpa-footer.png') } alt="Bioplatforms Australia" />
                      </a>
                </span>
                <span style={{paddingLeft: 30}}>
                    <a href="https://www.education.gov.au/national-collaborative-research-infrastructure-strategy-ncris">
                        <img className="footer-logos" src={ logoPNG('ncris-footer.png') } />
                    </a>
                </span>
            </div>
        </footer>
    );
}