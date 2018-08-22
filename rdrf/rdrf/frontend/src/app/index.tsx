import * as React from 'react';
import { connect } from 'react-redux';

import Instruction  from '../pages/proms_page/components/instruction';
import Question from '../pages/proms_page/components/question';

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

export default connect()(App);
