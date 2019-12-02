import * as React from 'react';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import Instruction from '../pages/proms_page/components/instruction';
import Question from '../pages/proms_page/components/question';
import { goNext, goPrevious, submitAnswers } from '../pages/proms_page/reducers';

import { isMobile } from 'react-device-detect';
import { GoChevronLeft, GoChevronRight } from 'react-icons/go';
import { Progress } from 'reactstrap';
import { Button, Col, Container, Row } from 'reactstrap';
import { ElementList } from '../pages/proms_page/logic';


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
    constructor(props) {
        super(props);
        this.moveNext = this.moveNext.bind(this);
        this.movePrevious = this.movePrevious.bind(this);
    }

    public atEnd() {
        const lastIndex = this.props.questions.length - 1;
        return this.props.stage === lastIndex;
    }

    public atBeginning() {
        return this.props.stage === 0;
    }


    public getProgress(): number {
        let numQuestions: number = this.props.questions.length;
        const consentQuestionCode = this.props.questions[numQuestions - 1].cde;
        // last question is considered as consent
        const allAnswers = Object.keys(this.props.answers).filter(val => {
            return val !== consentQuestionCode;
        });
        const numAnswers: number = allAnswers.length;
        numQuestions = numQuestions - 1; // consent not considered
        return Math.floor(100.00 * (numAnswers / numQuestions));
    }

    public movePrevious() {
        if (!this.atBeginning()) {
            this.props.goPrevious();
        }
    }

    public moveNext() {
        if (!this.atEnd()) {
            this.props.goNext();
        }
    }

    public render() {
        let nextButton;
        let backButton;
        let submitButton;
        let progressBar;
        let source;
        const style = { height: "100%" };

        if (this.atEnd()) {
            !isMobile ?
                nextButton = (<Col sm={{ size: 4, order: 2, offset: 1 }}>
                    <Button onClick={this.props.submitAnswers} color="success" size="sm">Submit Answers</Button>
                </Col>)
                :
                submitButton = (
                    <div className="text-center">
                        <Button onClick={this.props.submitAnswers} color="success" size="sm">Submit Answers</Button>
                    </div>
                )
        }
        else {
            nextButton = !isMobile ?
                (<Col sm={{ size: 2 }} style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <Button onClick={this.moveNext} size="sm" color="info" style={{ minWidth: '90px' }}>Next</Button>
                </Col>) :
                (<i onClick={this.moveNext}> <GoChevronRight style={{ fontSize: '56px' }} /> </i>)
        }

        if (this.atBeginning()) {
            backButton = !isMobile ?
                (<Col sm={{ size: 2 }} style={{ display: 'flex' }}>
                    <Button onClick={this.movePrevious} color="info" size="sm" disabled={true} style={{ minWidth: '90px' }}>Previous</Button>
                </Col>) : (<i onClick={this.movePrevious}> <GoChevronLeft style={{ fontSize: '56px' }} /> </i>)
        } else {
            backButton = !isMobile ?
                (<Col sm={{ size: 2 }} style={{ display: 'flex' }}>
                    <Button onClick={this.movePrevious} color="info" size="sm" style={{ minWidth: '90px' }}>Previous</Button>
                </Col>) : (<i onClick={this.movePrevious}> <GoChevronLeft style={{ fontSize: '56px' }} /> </i>)
        }

        if (!this.atEnd()) {
            progressBar = (
                <Col sm={{ size: 8 }}>
                    <Progress color="info" value={this.getProgress()}>{this.getProgress()}%</Progress>
                </Col>
            )
        }

        if (this.props.questions[this.props.stage].source) {
            source = (
                <div className="text-center text-muted" style={{ fontSize: '12px' }}> Source:
                    {this.props.questions[this.props.stage].source}
                </div>
            )
        }


        return (
            <div className="App" style={style}>
                <Container>
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
                        <Row className="navigationinputs">
                            {backButton}
                            {progressBar}
                            {nextButton}
                        </Row>
                    </div>
                    {submitButton}
                </Container>
                <footer className="footer" style={{ height: 'auto' }}>
                    {source}
                    <div className="text-center text-muted" style={{ fontSize: '12px' }}>
                        {this.props.questions[this.props.stage].copyright_text}
                    </div>
                </footer>
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
