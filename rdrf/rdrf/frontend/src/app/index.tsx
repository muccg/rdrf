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

class App extends React.Component<any> {

    render() {
        return (
            <div>
		Hello from React and Lee
            </div>
        );
    }

}

export default App;
