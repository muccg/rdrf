import * as React from 'react';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import Instruction  from '../pages/proms_page/components/instruction';
import Question from '../pages/proms_page/components/question';
import { goPrevious, goNext, submitAnswers } from '../pages/proms_page/reducers';

import { Button } from 'reactstrap';
import { Progress } from 'reactstrap';
import { Container, Row, Col } from 'reactstrap';

import { ElementList } from '../pages/proms_page/logic';
import * as ReactSwipe from 'react-swipe';

const swipeOptions = {
  callback() {
    console.log('question changed');
  },
  transitionEnd() {
    console.log('ended transition');
  }
};



interface AppInterface {
    title: string,
    stage: number,
    answers: any,
    questions: ElementList,
    goNext: any,
    goPrevious: any,
    submitAnswers: any,
}


class App extends React.Component<AppInterface, object> {
    private reactSwipe : ReactSwipe;
    atEnd() {
	let lastIndex = this.props.questions.length - 1;
	console.log("lastIndex = " + lastIndex.toString());
	console.log("stage = " + this.props.stage.toString());
	return this.props.stage == lastIndex;
    }

    getProgress(): number {
	let numQuestions: number = this.props.questions.length;
	let numAnswers : number = Object.keys(this.props.answers).length;
	return Math.floor(100.00 * ( numAnswers / numQuestions)) ; 
    }

    isNextButtonDisabled(): boolean {
	let questionCode = this.props.questions[this.props.stage].cde;
	return !(this.props.answers.hasOwnProperty(questionCode));
    }

    render() {
	var nextButton;
	if(this.atEnd()) {
	    console.log("at end");
	    nextButton = (<Button onClick={this.props.submitAnswers}>Submit Answers</Button>);
	}
	else {
	    console.log("not at end"); 
	    nextButton = (<Button disabled={this.isNextButtonDisabled()} onClick={this.props.goNext}>Next</Button>);
	};
	
        return (

		<div className="App">

	          <Container>
		<ReactSwipe ref={reactSwipe => this.reactSwipe = reactSwipe} className="mySwipe" swipeOptions={swipeOptions}>
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
		<Row>
		<Col sm={{ size: 4, order: 2, offset: 1 }}>
		<Progress color="info" value={this.getProgress()}>{this.getProgress()}%</Progress>
		</Col>
		</Row>
                </ReactSwipe>
		</Container>
		</div>

		        );
    }

}

function mapStateToProps(state) {
    return {stage: state.stage,
	    title: state.title,
	    answers: state.answers,
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
