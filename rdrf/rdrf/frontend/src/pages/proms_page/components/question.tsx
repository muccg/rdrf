import * as React from 'react';
import * as _ from 'lodash';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import { Form, FormGroup, Label, Input, Col, Row } from 'reactstrap';
import { QuestionInterface } from './interfaces';

import * as actions from '../reducers';
import Slider from 'rc-slider';
import Tooltip from "rc-tooltip";
import 'rc-slider/assets/index.css';


class Question extends React.Component<QuestionInterface, object> {
    constructor(props) {
        super(props);
    }

    handleChange(event) {
        console.log("radio button clicked");
        console.log(event);
        let cdeValue = event.target.value;
        let cdeCode = event.target.name;
        console.log("cde = " + cdeCode.toString());
        console.log("value = " + cdeValue.toString());
        this.props.enterData(cdeCode, cdeValue);
    }

    handleConsent(event) {
        let isConsentChecked = event.target.checked;
        let cdeCode = event.target.name;
        this.props.enterData(cdeCode, isConsentChecked);
    }

    onSliderChange = (value) => {
        console.log(value);
        let code = this.props.questions[this.props.stage].cde;
        this.props.enterData(code, value);
    }

    getMarks = (question) => {
        var minValue = question.spec.min;
        var maxValue = question.spec.max;
        const marks = {
            [minValue]: <strong>{minValue}</strong>,
            10:'10',
            20:'20',
            30:'30',
            40:'40',
            50:'50',
            60:'60',
            70:'70',
            80:'80',
            90:'90',
            [maxValue]: {
                  style: {
                    color: 'red',
                  },
                  label:<strong>{maxValue}</strong>,
                },
        };

        return marks;

    }

    getSliderHandle = () => {
        const Handle = Slider.Handle;
        const handle = props => {
            const { value, dragging, index, ...restProps } = props;
            return (
                <Tooltip
                    prefixCls="rc-slider-tooltip"
                    overlay={value}
                    visible={dragging}
                    placement="top"
                    key={index}
                    >
                    <Handle value={value} {...restProps} />
                </Tooltip>
                );
            };
        return handle;
    }



    render() {
        let question = this.props.questions[this.props.stage];
        const style = { width: "10%", height:"70vh", margin:"0 auto", padding: "100px" };
        const isConsent = (this.props.questions.length - 1) == this.props.stage;
        const consentText = "I consent to ongoing involvement in the CIC Cancer project" +
            "and receiving a reminder for the next survey.";

        return (
            <Form>
                <FormGroup tag="fieldset">
                    <legend>{this.props.questions[this.props.stage].title}</legend>
                    <i>{this.props.questions[this.props.stage].instructions}</i>
                </FormGroup>
                {
                    (question.spec.tag=='integer' ?
                        <div style={style}>
                            <Slider vertical min={question.spec.min}
                                    max={question.spec.max}
                                    marks={this.getMarks(question)}
                                    handle={this.getSliderHandle()}
                                    onChange={this.onSliderChange}
                                    />
                        </div>

                        :

                        isConsent ?
                        <FormGroup check>
                            <Label check>
                                <Input type="checkbox" name={this.props.questions[this.props.stage].cde}
                                    onChange={this.handleConsent.bind(this)}
                                    checked={this.props.answers[question.cde]} />
                                {consentText}
                            </Label>
                        </FormGroup>
                        :
                        _.map(question.spec.tag=='range' ? question.spec.options : [], (option, index) => (
                            <FormGroup check>
                                <Col sm="12" md={{ size: 6, offset: 3 }}>
                                    <Label check>
                                        <Input type="radio" name={this.props.questions[this.props.stage].cde} value={option.code}
                                            onChange={this.handleChange.bind(this)}
                                            checked={option.code === this.props.answers[question.cde]} />{option.text}
                                    </Label>
                                </Col>
                            </FormGroup>
                        ))
                    )
                }
            </Form>);
    }
}

function mapStateToProps(state) {
    return {
        questions: state.questions,
        stage: state.stage,
        answers: state.answers,
    };
}

function mapPropsToDispatch(dispatch) {
    return ({
        enterData: (cdeCode: string, cdeValue: any) => dispatch(actions.enterData({ cde: cdeCode, value: cdeValue })),
    });
}

export default connect<{}, {}, QuestionInterface>(mapStateToProps, mapPropsToDispatch)(Question);



