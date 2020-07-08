import * as _ from 'lodash';
import Slider, { Handle } from 'rc-slider';
import 'rc-slider/assets/index.css';
import Tooltip from "rc-tooltip";
import * as React from 'react';
import { connect } from 'react-redux';
import { Col, Form, FormGroup, Input, Label } from 'reactstrap';
import { InputType } from 'reactstrap/lib';
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
        this.props.enterData(cdeCode, cdeValue, true);
    }

    public handleInputChange = (event) => {
        const code = this.props.questions[this.props.stage].cde;
        this.props.enterData(code, event.target.value, true);
    }
    
    public handleDateInputChange = (event) => {
        const code = this.props.questions[this.props.stage].cde;
        const americanDatePattern = /^\d\d\d\d-\d\d-\d\d$/
        const isValid = americanDatePattern.test(event.target.value);
        this.props.enterData(code, event.target.value, isValid);
    }

    public transformSubstring = (mainString: string | string[], words: string[], transformation: string) : string[] => {
        const result = [];
        let mainArray: string[];
        if (typeof mainString === "string") {
            mainArray = mainString.split(' ');
        } else {
            mainArray = mainString;
        }
        switch(transformation) {
            case 'italic':
                for (const substring of mainArray) {
                    result.push(' ', <i>{substring}</i>);
                }
                return result;
            case 'underline':
                for (const substring of mainArray) {
                    if (words.includes(substring)) {
                        result.push(' ', <u>{substring}</u>);
                    } else {
                        result.push(' ', substring);
                    }
                }
                return result;
            case 'bullet':
              const ul = []
              let line = [];
              let noBullet = false;
              let firstWord = true;
              for (const substringword of mainArray) {
                  const word = substringword + "";
                  if (word.slice(-1) === '.') {
                      line.push(word);
                      if (noBullet === true) {  // if the sentence starts with 0, no bullet
                        result.push(<div>{line}</div>);
                      }else {
                        result.push(<li>{line}</li>);
                      }
                      line = [];
                      noBullet = false;
                      firstWord = true;
                  } else {
                        if (firstWord === true && word === '0'){
                            // if the first non-blank word is '0', no bullet
                            noBullet = true;
                            firstWord = false;
                        }
                        line.push(substringword);
                        if (word !== ' ' && word !== ''){
                            // element after a word ending in a '.' (period) is ' ' (blank) in the array
                            // if there is a newline after '.' then the array will have '' for that
                            // so if the current element is one such, it is not treated as first word
                            // the first substring having characters is counted as first word
                            firstWord = false;
                        }
                  }
              }
              ul.push(<ul>{result}</ul>);
              return ul;
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

        this.props.enterData(cdeCode, values, true);
    }

    public handleConsent(event) {
        const isConsentChecked = event.target.checked;
        const cdeCode = event.target.name;
        this.props.enterData(cdeCode, isConsentChecked, true);
    }

    public onSliderChange = (value) => {
        const code = this.props.questions[this.props.stage].cde;
        this.props.enterData(code, value, true);
    }

    public getMarks = (question) => {
        const minValue = question.spec.params.min;
        const maxValue = question.spec.params.max;

        const minMark = {
            [minValue]: {
                style: {
                    color: 'red', width: 'max-content', textAlign: 'left', marginBottom: '-100%'
                },
                label: <strong>{minValue} - {question.spec.widget_spec.min_label}</strong>,
            }
        };

        const midMarks = {}
        const diff = ((maxValue - minValue)>10) ? (maxValue - minValue) / 10 : 1;
        for(let mark = minValue+diff; mark<maxValue; mark+=diff) {
           midMarks[mark] = mark + "";
        }

        const maxMark = {
            [maxValue]: {
                style: {
                    color: 'green', width: 'max-content', textAlign: 'left', marginBottom: '-100%'
                },
                label: <strong>{maxValue} - {question.spec.widget_spec.max_label}</strong>,
            }
        };

        return Object.assign({}, minMark, midMarks, maxMark);
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

    public renderOptions(question: any) {
        return _.map(question.spec.options, (option, index) => (
                <FormGroup check={true}>
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <Label check={true}>
                            <Input type="radio" name={this.props.questions[this.props.stage].cde} value={option.code}
                                onChange={this.handleChange}
                                checked={option.code === this.props.answers[question.cde]} />{option.text}
                        </Label>
                    </Col>
                </FormGroup>
            ));
    }

    public renderRange(question: any) {
        return (
            <Form>
                <FormGroup tag="fieldset">
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <h6>{question.survey_question_instruction}</h6>
                        <h4>{question.title}</h4>
                        <h6>{question.instructions}</h6>
                    </Col>
                </FormGroup>
                {this.renderOptions(question)}
            </Form>
        );
    }

    public renderMultiselect(question: any) {
	let defaultValue:string = ""; 
        if (this.props.answers[question.cde] !== undefined) {
	    defaultValue = this.props.answers[question.cde].toString().replace("[","").replace("]","");
	}
	    
        return (
            <Form>
                <FormGroup tag="fieldset">
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <h6>{question.survey_question_instruction}</h6>
                        <h4>{question.title}</h4>
                        <h6>{question.instructions}</h6>
                    </Col>
                </FormGroup>
                <FormGroup>
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <Input type="select"
                            name={question.cde}
	                    defaultValue={defaultValue}
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

    public handleIntegerChange = (event) => {
        if (/^([-]?[0-9]+)?$/.test(event.target.value) && !(/^-$/.test(event.target.value))) {
            event.target.classList.remove('is-invalid');
            const code = this.props.questions[this.props.stage].cde;
            this.props.enterData(code, event.target.value, true);  // set state to true
        } else {
            event.target.classList.add('is-invalid');
            const code = this.props.questions[this.props.stage].cde;
            this.props.enterData(code, event.target.value, false);  // set state to false
        }
    }

    public renderInteger(question: any) {
        let currentValue = "";
        if (this.props.answers[question.cde] !== undefined) {
            currentValue = this.props.answers[question.cde];
        }
        return (
            <Form>
                <FormGroup tag="fieldset">
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <h6>{question.survey_question_instruction}</h6>
                        <h4>{question.title}</h4>
                        <h6>{question.instructions}</h6>
                    </Col>
                </FormGroup>
                <FormGroup>
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <Input type="text"
                            name={question.cde}
                            onChange={this.handleIntegerChange}
                            onKeyDown={this.handleInputKeyDown}
                            value={currentValue}
                        />
                    </Col>
                </FormGroup>
            </Form>
        );
    }

    public renderSlider(question: any) {
        const boxStyle = { width: "100px", height: "100px", backgroundColor: "#666",
                           marginTop: "20vh", paddingTop: "3px", borderRadius: "8px" };
        const pStyle = { color: "white", align: "center" };
        const style = { width: "50%", height: "50vh", margin: "0 auto", leftPadding: "100px" };

        let transformedInstruction: string[] | string;
        if (question.cde === 'EQ_Health_Rate') {
            transformedInstruction = this.transformSubstring(this.props.questions[this.props.stage].instructions,
                                                              ['best', 'worst'], 'underline');
            transformedInstruction = this.transformSubstring(transformedInstruction, [], 'bullet');
        } else {
            if (question.cde === 'EQ_UsualActivities') {
                transformedInstruction = this.transformSubstring(this.props.questions[this.props.stage].instructions,
                                                                  [], 'italic');
            } else {
                transformedInstruction = this.props.questions[this.props.stage].instructions;
            }
        }

        let defaultValue = null;
        if (this.props.answers[question.cde] !== undefined) {
            defaultValue = this.props.answers[question.cde];
        } else {
            this.onSliderChange(defaultValue);
        }

        return (
            <Form>
                <FormGroup tag="fieldset">
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <h6>{this.props.questions[this.props.stage].survey_question_instruction}</h6>
                        <h4>{this.props.questions[this.props.stage].title}</h4>
                        <h6>{transformedInstruction}</h6>
                    </Col>
                </FormGroup>
                <FormGroup>
                    <div className='row'>
                        <div className="col">
                            <div className="float-right" style={boxStyle}>
                                <p className="text-center" style={pStyle}>
                                    <p>{question.spec.widget_spec.box_label} <br /> <b>{defaultValue}</b></p>
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
                </FormGroup>
            </Form>
        );
    }

    public renderText(question: any) {
        return (
            <Form>
                <FormGroup tag="fieldset">
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <h6>{question.survey_question_instruction}</h6>
                        <h4>{question.title}</h4>
                        <h6>{question.instructions}</h6>
                    </Col>
                </FormGroup>
                <FormGroup>
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <Input type="text"
                            name={question.cde}
                            onChange={this.handleInputChange}
                            onKeyDown={this.handleInputKeyDown}
                        />
                    </Col>
                </FormGroup>
            </Form>
        );
    }

    public handleFloatChange = (event) => {
        if ((/^([-]?[0-9]+(\.[0-9]+)?)?$/.test(event.target.value)) && !(/^-$/.test(event.target.value))) {
            event.target.classList.remove('is-invalid');
            const code = this.props.questions[this.props.stage].cde;
            this.props.enterData(code, event.target.value, true);
        } else {
            event.target.classList.add('is-invalid');
            const code = this.props.questions[this.props.stage].cde;
            this.props.enterData(code, event.target.value, false);
        }
    }

    public renderFloat(question: any) {
        let currentValue = "";
        if (this.props.answers[question.cde] !== undefined) {
            currentValue = this.props.answers[question.cde];
        }
        return (
            <Form>
                <FormGroup tag="fieldset">
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <h6>{question.survey_question_instruction}</h6>
                        <h4>{question.title}</h4>
                        <h6>{question.instructions}</h6>
                    </Col>
                </FormGroup>
                <FormGroup>
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <Input type="text"
                            name={question.cde}
                            onChange={this.handleFloatChange}
                            onKeyDown={this.handleInputKeyDown}
                            value={currentValue}
                        />
                    </Col>
                </FormGroup>
            </Form>
        );
    }

    public renderDate(question: any) {
        let currentValue = null;
        if (this.props.answers[question.cde] !== undefined) {
            currentValue = this.props.answers[question.cde];
        }
        return (
            <Form>
                <FormGroup tag="fieldset">
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <h6>{question.survey_question_instruction}</h6>
                        <h4>{question.title}</h4>
                        <h6>{question.instructions}</h6>
                    </Col>
                </FormGroup>
                <FormGroup>
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <Input type="date"
                            {...question.spec.params}
                            name={question.cde}
                            onChange={this.handleDateInputChange}
                            onKeyDown={this.handleInputKeyDown}
                            value={currentValue}
                        />
                    </Col>
                </FormGroup>
            </Form>
        );
    }

    private renderConsent(question) {
        const consentText = <div>By ticking this box you:
            <ul>
                <li>Give consent for the information you provide to be used for the CIC Cancer project; and </li>
                <li>Will receive a reminder when the next survey is due.</li>
            </ul>
        </div>;
        return (
            <Form>
                <FormGroup tag="fieldset">
                    <Col sm="12" md={{ size: 6, offset: 3 }}>
                        <h6>{question.survey_question_instruction}</h6>
                        <h4>{question.title}</h4>
                        <h6>{question.instructions}</h6>
                    </Col>
                </FormGroup>
                <FormGroup check={true}>
                    <Label check={true}>
                        <Input type="checkbox" name={this.props.questions[this.props.stage].cde}
                            onChange={this.handleConsent}
                            checked={this.props.answers[question.cde]} />
                        {consentText}
                    </Label>
                </FormGroup>
            </Form>
        );
    }

    public render() {
        const question = this.props.questions[this.props.stage];
        switch (question.spec.ui) {
            case "integer-normal": return this.renderInteger(question);
            case "integer-slider": return this.renderSlider(question);
            case "float": return this.renderFloat(question);
            case "text": return this.renderText(question);
            case "date": return this.renderDate(question)
            case "range": return this.renderRange(question);
            case "multi_select": return this.renderMultiselect(question);
            case "consent": return this.renderConsent(question);
        };
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
        enterData: (cdeCode: string, cdeValue: any, isValidValue: boolean ) => dispatch(actions.enterData({ cde: cdeCode, value: cdeValue, isValid: isValidValue })),
    });
}

export default connect<{}, {}, QuestionInterface>(mapStateToProps, mapPropsToDispatch)(Question);
