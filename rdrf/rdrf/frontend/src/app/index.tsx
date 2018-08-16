import * as _ from 'lodash';
import * as React from 'react';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import {
    BrowserRouter as Router,
    Link,
    Route,
    Redirect,
    Switch,
    withRouter,
 } from 'react-router-dom';

import {
    Alert,
    Container,
    Col,
    Nav,
    Navbar,
    NavbarBrand,
    NavItem,
    Row,
} from 'reactstrap';

import Header from './header';
import Routes from './routes';
import Footer from './footer';

import LoginInProgressPage from '../pages/login_in_progress_page';
import LoginRequiredPage from '../pages/login_required_page';

import { getCKANAuthInfo } from '../reducers/auth';

class App extends React.Component<any> {
    componentWillMount() {
        if (window.otu_search_config.ckan_auth_integration) {
            this.props.getCKANAuthInfo();
        }
    }

    render() {
        return (
            <div>
                <Header userEmailAddress={this.props.auth.email} />
                { this.renderContents() }

                { /* TODO
                    Port the footer into React as well. Currently it is provided by the base.html Django template.
                    What is preventing porting it for now is the wrapping logic. Check .content-div in bpaotu.css for more details.
                <Footer /> */}
            </div>
        );
    }

    renderContents() {
        if (window.otu_search_config.ckan_auth_integration) {
            if (this.props.auth.isLoginInProgress) {
                return <LoginInProgressPage />
            }
            if (!this.props.auth.isLoggedIn) {
                return <LoginRequiredPage />
            }
        }
        return <Routes />
    }
}



function mapStateToProps(state) {
    return {
        auth: state.auth
    }
}

function mapDispatchToProps(dispatch) {
    return bindActionCreators({
        getCKANAuthInfo,
    }, dispatch);
}

export default withRouter(connect(mapStateToProps, mapDispatchToProps)(App) as any);
