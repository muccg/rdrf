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

import Instruction  from '../pages/proms_page/components/instruction';
import Question from '../pages/proms_page/components/question';
import rootReducer from '../reducers';


class App extends React.Component<any> {

    render() {
        return (
		<div>
		   <Instruction />
		   <Question />
                </div>
        );
    }

}

export default App;
