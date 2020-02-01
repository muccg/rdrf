import * as _ from 'lodash';
import Slider, { Handle } from 'rc-slider';
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
        this.handleMultiChange = this.handleMultiChange.bind(this);
    }

    public handleChange(event) {
        const cdeValue = event.target.value;
        const cdeCode = event.target.name;
        this.props.enterData(cdeCode, cdeValue);
    }

    public handleInputChange = (event) => {
        const code = this.props.questions[this.props.stage].cde;
        this.props.enterData(code, event.target.value);
    }

    public transformSubstring = (mainString: string, words: string[], transformation: string) => {
        var result = [];
        switch(transformation) {
            case 'underline':
                const mainArray = mainString.split(' ');
                for (var i = 0; i < mainArray.length; i++) {
                    var substring = mainArray[i]
                    if (words.includes(substring)){
                        result = result.concat( [ ' ', <u>{substring}</u>] )
                    } else {
                        result = result.concat( [ ' ', substring ] )
                    }
                }
                return result;
                break;
        }
    }

    public handleInputKeyDown = (event) => {
        // ignore Enter key.
        if (event.key === 'Enter') {
            event.preventDefault();
        }
    }

    public handleMultiChange(event) {
        const cdeCode = event.target.name;
        let values;
        let options;
        options = event.target.options;
        values = [];
        _.each(event.target.options, (option: HTMLOptionElement) => {
            if (option.selected) {
                values.push(option.value);
            }
        });

        this.props.enterData(cdeCode, values);
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
            [minValue]: {
                style: {
                    color: 'red', width: 'max-content'
                },
                label: <strong>{minValue} - The worst health you can imagine</strong>,
            },
            10: '10',
            20: '20',
            30: '30',
            40: '40',
            50: '50',
            60: '60',
            70: '70',
            80: '80',
            90: '90',
            [maxValue]: {
                style: {
                    color: 'green', width: 'max-content'
                },
                label: <strong>{maxValue} - The best health you can imagine</strong>,
            },
        };

        return marks;
    }

    public getSliderHandle = () => {
        // const Handle = Slider.Handle;
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

    public renderMultiSelect(question: any) {
        return (
            <Form>
                <FormGroup tag="fieldset">
                    <h6><i>{question.survey_question_instruction}</i></h6>
                    <h4>{question.title}</h4>
                    <i>{question.instructions}</i>
                </FormGroup>
                <FormGroup>
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <Input type="select"
                            name={question.cde}
                            onChange={this.handleMultiChange} multiple={true} >
                            {_.map(question.spec.options, (option, index) => (
                                <option key={option.code} value={option.code}>
                                    {option.text}
                                </option>
                            ))
                            }
                        </Input>
                    </Col>
                </FormGroup>
            </Form>
        );
    }

    public renderInput(question: any) {
        let defaultValue = ""
        if (this.props.answers[question.cde]) {
            defaultValue = this.props.answers[question.cde]
        }

        return (
            <Form>
                <FormGroup tag="fieldset">
                    <h6><i>{question.survey_question_instruction}</i></h6>
                    <h4>{question.title}</h4>
                    <i>{question.instructions}</i>
                </FormGroup>
                <FormGroup>
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <Input type="text"
                            name={question.cde}
                            onChange={this.handleInputChange}
                            onKeyDown={this.handleInputKeyDown}
                            value={defaultValue}
                        />
                    </Col>
                </FormGroup>
            </Form >
        );
    }

    public render() {
        const question = this.props.questions[this.props.stage];
        let defaultValue = 0;
        if (question.spec && question.spec.tag === 'integer') {
            if (this.props.answers[question.cde] !== undefined) {
                defaultValue = this.props.answers[question.cde];
            } else {
                this.onSliderChange(defaultValue);
            }
        }
        const boxStyle = { width: "100px", height: "100px", backgroundColor: "#666",
                           marginTop: "20vh", paddingTop: "3px", borderRadius: "8px" };
        const pStyle = { color: "white", align: "center" };
        const style = { width: "50%", height: "50vh", margin: "0 auto", leftPadding: "100px" };
        const isLast = (this.props.questions.length - 1) === this.props.stage;

        const isConsent = question.cde === "PROMSConsent";
        const consentText = <div>By ticking this box you:
                                <ul>
                <li>Give consent for the information you provide to be used for the CIC Cancer project; and </li>
                <li>Will receive a reminder when the next survey is due.</li>
            </ul>
        </div>;
        const isMultiSelect = (question.spec && question.spec.tag === 'range') && question.spec.allow_multiple;

        if ((question.tag === "cond" && question.spec == null) || question.datatype === "string") {
            return this.renderInput(question);
        }

        if (isMultiSelect) {
            return this.renderMultiSelect(question);
        }

        let transformed_instruction;
        if (question.cde === 'EQ_Health_Rate') {
            var words = ['best', 'worst']; // words to be transformed
            transformed_instruction = this.transformSubstring(this.props.questions[this.props.stage].instructions,
                                                              words,
                                                              'underline')
        } else {
            transformed_instruction = this.props.questions[this.props.stage].instructions
        }

        return (
            <Form>
                <FormGroup tag="fieldset">
                    <h6><i>{this.props.questions[this.props.stage].survey_question_instruction}</i></h6>
                    <h4>{this.props.questions[this.props.stage].title}</h4>
                    <i>{transformed_instruction}</i>
                </FormGroup>
                {
                    (question.spec.tag === 'integer' ?
                        <div className='row'>
                            <div className="col">
                                <div className="float-right" style={boxStyle}>
                                    <p className="text-center" style={pStyle}>
                                        <p>YOUR HEALTH TODAY <br></br> <b>{defaultValue}</b></p>
                                    </p>
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
                            _.map(question.spec.tag === 'range' ? question.spec.options : [], (option, index) => (
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
