import * as React from 'react';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import Instruction  from '../pages/proms_page/components/instruction';
import Question from '../pages/proms_page/components/question';
import { goPrevious, goNext, submitAnswers } from '../pages/proms_page/reducers';

import { Button } from 'reactstrap';
import { Container, Row, Col } from 'reactstrap';

import { ElementList } from '../pages/proms_page/logic';

interface AppInterface {
    title: string,
    stage: number,
    questions: ElementList,
    goNext: any,
    goPrevious: any,
    submitAnswers: any,
}


class App extends React.Component<AppInterface, object> {
    atEnd() {
	let lastIndex = this.props.questions.length - 1;
	console.log("lastIndex = " + lastIndex.toString());
	console.log("stage = " + this.props.stage.toString());
	return this.props.stage == lastIndex;
    }

    render() {
	var nextButton;
	if(this.atEnd()) {
	    console.log("at end");
	    nextButton = (<Button onClick={this.props.submitAnswers}>Submit Answers</Button>);
	}
	else {
	    console.log("not at end"); 
	    nextButton = (<Button onClick={this.props.goNext}>Next</Button>);
	};
	
        return (

		<div className="App">
	          <Container>
                    <Row>
		     <Col>
		       <Instruction stage={this.props.stage} />
		     </Col>
                    </Row>

                    <Row>
		      <Col>
		       <Question title={this.props.title} stage={this.props.stage} questions={this.props.questions}/>
		      </Col>
                    </Row>

		  <Row>
		    <Col>
		      <Button onClick={this.props.goPrevious} >Prev</Button>
		    </Col>
		    <Col>
		      {nextButton}
		    </Col>
		  </Row>
		</Container>
		</div>

		        );
    }

}

function mapStateToProps(state) {
    return {stage: state.stage,
	    title: state.title,
	    questions: state.questions}
}

function mapDispatchToProps(dispatch) {
return bindActionCreators({
    goNext,
    goPrevious,
    submitAnswers,
     }, dispatch);
}

export default connect(mapStateToProps,mapDispatchToProps)(App);
