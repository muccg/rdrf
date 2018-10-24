import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import Instruction  from '../pages/proms_page/components/instruction';
import Question from '../pages/proms_page/components/question';
import { goPrevious, goNext, submitAnswers } from '../pages/proms_page/reducers';

import { Button } from 'reactstrap';
import { Progress } from 'reactstrap';
import { Container, Row, Col } from 'reactstrap';

import { ElementList } from '../pages/proms_page/logic';

//import * as Swipe from 'react-easy-swipe';

import Swipe from 'react-easy-swipe';
 


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
    atEnd() {
	let lastIndex = this.props.questions.length - 1;
	console.log("lastIndex = " + lastIndex.toString());
	console.log("stage = " + this.props.stage.toString());
	return this.props.stage == lastIndex;
	}
	
	atBegin() {
	    let firstIndex = 0;
	    console.log("firstIndex = " + firstIndex.toString());
	    console.log("stage = " + this.props.stage.toString());
	    return this.props.stage == firstIndex;
	}

    getProgress(): number {
	let numQuestions: number = this.props.questions.length;
	let numAnswers : number = Object.keys(this.props.answers).length;
	return Math.floor(100.00 * ( numAnswers / numQuestions)) ; 
    }

    isNextButtonDisabled(): boolean {
	try {
	    let questionCode = this.props.questions[this.props.stage].cde;
	    return !(this.props.answers.hasOwnProperty(questionCode));
	}
	catch(err) {
	    return false;
	}
    }

    onSwipeMove(position, event) {
	console.log("swipemove " + position.y.toString());
	if (!this.atEnd() && !this.isNextButtonDisabled()) {
	    if (position.y < -5) {
	        this.props.goNext();
	    }
	}
	if (!this.atBegin()) {
		if (position.y > 5) {
			this.props.goPrevious();
		}
	}
    }

    render() {
	var nextButton;

	if(this.atEnd()) {
	    console.log("at end");
	    nextButton = (<Button onClick={this.props.submitAnswers}>Submit Answers</Button>);
	}
	else {
	    console.log("not at end"); 
	    //nextButton = (<Button disabled={this.isNextButtonDisabled()} onClick={this.props.goNext}>Next</Button>);
	    nextButton = " ";//(<Button disabled={this.isNextButtonDisabled()} onClick={this.props.goNext}>Next</Button>);
	};
	
        return (

		<div className="App">
	          <Container>
		<Swipe onSwipeMove={this.onSwipeMove.bind(this)}> 

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
		      {nextButton}
		    </Col>
		  </Row>
		<Row>
		<Col sm={{ size: 4, order: 2, offset: 1 }}>
		<Progress color="info" value={this.getProgress()}>{this.getProgress()}%</Progress>
		</Col>
		</Row>
		</Swipe>
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
