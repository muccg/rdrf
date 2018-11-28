import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import Instruction from '../pages/proms_page/components/instruction';
import Question from '../pages/proms_page/components/question';
import { goPrevious, goNext, submitAnswers } from '../pages/proms_page/reducers';

import { Button } from 'reactstrap';
import { Progress } from 'reactstrap';
import { Container, Row, Col } from 'reactstrap';

import { ElementList } from '../pages/proms_page/logic';

import Swipe from 'react-easy-swipe';
import { isMobile } from 'react-device-detect';


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

    atBeginning() {
        return this.props.stage == 0;
    }


    getProgress(): number {
        let numQuestions: number = this.props.questions.length;
        let consentQuestionCode = this.props.questions[numQuestions - 1].cde;
        // last question is considered as consent
        let allAnswers = Object.keys(this.props.answers).filter(val => {
            return val != consentQuestionCode;
        });
        let numAnswers: number = allAnswers.length;
        numQuestions = numQuestions - 1; // consent not considered
        return Math.floor(100.00 * (numAnswers / numQuestions));
    }

    onSwipeRight(position, event) {
        if (!this.atBeginning()) {
            this.props.goPrevious();
        }
    }

    onSwipeLeft(position, event) {
        if (!this.atEnd()) {
            this.props.goNext();
        }
    }

    render() {
        var nextButton;
        var backButton;
        var submitButton;
        var progressBar;

        if (this.atEnd()) {
            console.log("at end");
            !isMobile ? 
            nextButton = (<Col sm={{ size: 4, order: 2, offset: 1 }}>
                <Button onClick={this.props.submitAnswers} color="success" size="sm">Submit Answers</Button>
            </Col>)
            :
            submitButton = (
                <Row>
                    <Col sm={{ size: 4, order: 2, offset: 1 }}>
                        <Button onClick={this.props.submitAnswers} color="success" size="sm">Submit Answers</Button>
                    </Col>
                </Row>           
            )
        }
        else {
            console.log("not at end");
            nextButton = !isMobile ? 
              (<Col sm={{ size: 1, order: 3, offset: 1 }}>
                <Button onClick={this.onSwipeLeft.bind(this)} size="sm" color="info">Next</Button>
            </Col>) : "";
        }

        if (this.atBeginning()) {
            backButton = !isMobile ? 
              (<Col sm={{ size: 1 }}>
                <Button onClick={this.onSwipeRight.bind(this)} color="info" size="sm" disabled>Previous</Button>
               </Col>) : "";
        } else {
            backButton = !isMobile ? 
              (<Col sm={{ size: 1 }}>
                <Button onClick={this.onSwipeRight.bind(this)} color="info" size="sm">Previous</Button>
               </Col>) : "";
        }

        if (!this.atEnd()) {
            progressBar = (
                <Col>
                    <Progress color="info" value={this.getProgress()}>{this.getProgress()}%</Progress>
                </Col>
            )
        }

        return (
            <div className="App">
                <Container>
                    <Swipe onSwipeLeft={this.onSwipeLeft.bind(this)}
                        onSwipeRight={this.onSwipeRight.bind(this)}>
                        <div className="mb-4">
                            <Row>
                                <Col>
                                    <Instruction stage={this.props.stage} />
                                </Col>
                            </Row>

                            <Row>
                                <Col>
                                    <Question title={this.props.title} stage={this.props.stage} questions={this.props.questions} />
                                </Col>
                            </Row>
                        </div>

                        <div className="mb-4">
                        <Row>
                            {backButton}
                            {progressBar}
                            {nextButton}
                        </Row>
                        </div>
                        {submitButton}
                    </Swipe>
                </Container>
            </div>
        );
    }
}

function mapStateToProps(state) {
    return {
        stage: state.stage,
        title: state.title,
        answers: state.answers,
        questions: state.questions
    }
}

function mapDispatchToProps(dispatch) {
    return bindActionCreators({
        goNext,
        goPrevious,
        submitAnswers,
    }, dispatch);
}

export default connect(mapStateToProps, mapDispatchToProps)(App);
