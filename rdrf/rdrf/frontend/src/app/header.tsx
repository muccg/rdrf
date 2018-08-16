import * as _ from 'lodash';
import * as React from 'react';
import {
    Nav,
    Navbar,
    NavbarBrand,
    NavItem,
    NavLink,
    NavbarToggler,
    Collapse,
 } from 'reactstrap';

import Octicon from '../components/octicon';
import {
    Link,
    NavLink as RRNavLink
} from 'react-router-dom';

export default class Header extends React.Component<any, any> {
    constructor(props) {
        super(props);

        this.toggle = this.toggle.bind(this);
        this.state = {
            isOpen: false
        }
    }

    toggle() {
        this.setState({
            isOpen: !this.state.isOpen
        })
    }

    render() {
        const logoPNG = _.join([window.otu_search_config.static_base_url, 'bpa-logos', 'bpalogo_withdataportal.png'], '/');
        return (
            <Navbar color="light" light expand="lg">
                <NavbarBrand className="site-header-logo" href="https://data.bioplatforms.com/">
                    <img src={logoPNG} alt="Bioplatform Australia" />
                </NavbarBrand>
                <NavbarToggler onClick={this.toggle} />
                <Collapse isOpen={this.state.isOpen} navbar>
                    <Nav className="navbar-nav">
                        <NavItem>
                            <NavLink href="https://data.bioplatforms.com/organization/about/australian-microbiome">
                                Australian Microbiome Home
                            </NavLink>
                        </NavItem>

                        <NavItem>
                            <NavLink exact to='/' activeClassName="active" tag={RRNavLink}>Search</NavLink>
                        </NavItem>

                        <NavItem>
                            <NavLink to='/map' activeClassName="active" tag={RRNavLink}>Map</NavLink>
                        </NavItem>

                        <NavItem>
                            <NavLink to='/contextual' activeClassName="active" tag={RRNavLink}>Contextual</NavLink>
                        </NavItem>
                    </Nav>
                    <Nav className="ml-auto" navbar>
                        <NavItem>
                                { this.props.userEmailAddress ?
                                    <div>
                                        <Octicon name="person" />
                                        <span className="site-header-username">
                                            { this.props.userEmailAddress }
                                        </span>
                                    </div> : ''
                                }
                        </NavItem>
                    </Nav>
               </Collapse>
            </Navbar>)
    }
}
