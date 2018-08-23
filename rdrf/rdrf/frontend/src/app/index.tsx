import * as React from 'react';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import Instruction  from '../pages/proms_page/components/instruction';
import Question from '../pages/proms_page/components/question';
import { goPrevious, goNext } from '../pages/proms_page/reducers';

import { Button } from 'reactstrap';


class App extends React.Component<any> {

    render() {
        return (
		<div>
		<Instruction stage={this.props.stage} />
		
		<Question stage={this.props.stage} />

		<Button onClick={this.props.goPrevious} >Prev</Button>   <Button onClick={this.props.goNext}>Next</Button>
		
                </div>
        );
    }

}

function mapStateToProps(state) {
    return {stage: state.stage}
}

function mapDispatchToProps(dispatch) {
return bindActionCreators({
    goNext,
    goPrevious,
     }, dispatch);
}

export default connect(mapStateToProps,mapDispatchToProps)(App);
