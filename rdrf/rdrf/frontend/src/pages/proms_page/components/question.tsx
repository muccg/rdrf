import * as React from 'react';
import * as _ from 'lodash';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import { Form, FormGroup, Label, Input } from 'reactstrap';
import { QuestionInterface } from './interfaces';

import * as actions from '../reducers';



class Question extends React.Component<QuestionInterface, object> {
    constructor(props) {
      super(props);
    }
    handleChange(event) {
	console.log("radio button clicked");
	console.log(event);
	let cdeValue  = event.target.value;
	let cdeCode = event.target.name;
	console.log("cde = " + cdeCode.toString());
	console.log("value = " + cdeValue.toString());
	this.props.enterData(cdeCode, cdeValue);
    }
    
    
    render() {
	return ( 
		<Form>	 
                   <FormGroup tag="fieldset">
                <legend>{this.props.questions[this.props.stage].title}</legend>
		   </FormGroup>

		  {
                      _.map(this.props.questions[this.props.stage].options, (option, index) => (
		          <FormGroup check>
		            <Label check>
	                      <Input type="radio" name={this.props.questions[this.props.stage].cde} value={option.code}
                          onChange={this.handleChange.bind(this)}/>{option.text}
		            </Label>
                          </FormGroup>

                      ))
                  }

		</Form>);
    }
}

function mapStateToProps(state) {
    return {questions: state.questions,
	    stage: state.stage,
	    
	   };
}

function mapPropsToDispatch(dispatch) {
    return ({
	enterData: (cdeCode:string, cdeValue: any) => dispatch(actions.enterData({cde:cdeCode, value:cdeValue})),
    });
}

export default connect<{},{},QuestionInterface>(mapStateToProps, mapPropsToDispatch)(Question);

	

