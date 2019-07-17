import * as _ from 'lodash';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import Tooltip from "rc-tooltip";
import * as React from 'react';
import { connect } from 'react-redux';
import { Col, Form, FormGroup, Input, Label } from 'reactstrap';
import { QuestionInterface } from './interfaces';

import * as actions from '../reducers';



class Question extends React.Component<QuestionInterface, object> {
    constructor(props) {
        super(props);
        this.onSliderChange = this.onSliderChange.bind(this);
        this.handleConsent = this.handleConsent.bind(this);
        this.handleChange = this.handleChange.bind(this);
    }

    public handleChange(event) {
        const cdeValue = event.target.value;
        const cdeCode = event.target.name;
        this.props.enterData(cdeCode, cdeValue);
    }

    public handleConsent(event) {
        const isConsentChecked = event.target.checked;
        const cdeCode = event.target.name;
        this.props.enterData(cdeCode, isConsentChecked);
    }

    public onSliderChange = (value) => {
        const code = this.props.questions[this.props.stage].cde;
        this.props.enterData(code, value);
    }

    public getMarks = (question) => {
        const minValue = question.spec.min;
        const maxValue = question.spec.max;
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

    public getSliderHandle = () => {
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


    public render() {
        const question = this.props.questions[this.props.stage];
        let defaultValue = 0;
        if (question.spec.tag === 'integer') {
            if(this.props.answers[question.cde] !== undefined) {
                defaultValue = this.props.answers[question.cde];
            } else {
                this.onSliderChange(defaultValue);
            }
        }
        const boxStyle = {width: "100px", height:"100px", backgroundColor: "black"};
        const pStyle = {color: "white", align: "center"};
        const style = { width: "50%", height:"50vh", margin:"0 auto", leftPadding: "100px" };
        const isLast = (this.props.questions.length - 1) === this.props.stage;
	    const isConsent = question.cde === "PROMSConsent";
        const consentText = <div>By ticking this box you:
                                <ul>
                                    <li>Give consent for the information you provide to be used for the CIC Cancer project; and </li>
                                    <li>Will receive a reminder when the next survey is due.</li>
                                </ul>
                            </div>;

        return (
            <Form>
                <FormGroup tag="fieldset">
                    <h6><i>{this.props.questions[this.props.stage].survey_question_instruction}</i></h6>
                    <h4>{this.props.questions[this.props.stage].title}</h4>
                    <i>{this.props.questions[this.props.stage].instructions}</i>
                </FormGroup>
                {
                    (question.spec.tag === 'integer' ?
                        <div className='row'>
                            <div className="col">
                                <div className="float-right" style={boxStyle}>
                                    <p className="text-center" style={pStyle}>YOUR HEALTH RATE TODAY <b>{defaultValue}</b></p>
                                </div>
                            </div>
                            <div className="col" style={style}>
                                <Slider vertical={true} min={question.spec.min}
                                    max={question.spec.max}
                                    defaultValue={defaultValue}
                                    marks={this.getMarks(question)}
                                    handle={this.getSliderHandle()}
                                    onChange={this.onSliderChange}
                                />
                            </div>
                        </div>

                        :

                        isConsent ?
                        <FormGroup check={true}>
                            <Label check={true}>
                                <Input type="checkbox" name={this.props.questions[this.props.stage].cde}
                                    onChange={this.handleConsent}
                                    checked={this.props.answers[question.cde]} />
                                {consentText}
                            </Label>
                        </FormGroup>
                        :
                        _.map(question.spec.tag==='range' ? question.spec.options : [], (option, index) => (
                            <FormGroup check={true}>
                                <Col sm="12" md={{ size: 6, offset: 3 }}>
                                    <Label check={true}>
                                        <Input type="radio" name={this.props.questions[this.props.stage].cde} value={option.code}
                                            onChange={this.handleChange}
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



