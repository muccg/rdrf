import * as React from 'react';
import * as _ from 'lodash';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import { Form, FormGroup, Label, Input } from 'reactstrap';
import { QuestionInterface } from './interfaces';
import { fetchQuestionData } from '../reducers';


// todo hook this up
function mapDispatchToProps(dispatch) {
    return bindActionCreators({
	      fetchQuestionData},
              dispatch);
}

export default class Question extends React.Component<any> {
    componentDidMount() {
	//this.props.fetchData(this.props.stage);
    }

    render() {
	return ( 
		<Form>	 
                   <FormGroup tag="fieldset">
                       <legend>Question {this.props.questions[this.props.stage].text}</legend>
		   </FormGroup>


		  {
                      _.map(this.props.questions[this.props.stage].options, (option, index) => (
		          <FormGroup check>
		            <Label check>
	                      <Input type="radio" name="radio1" value="{option.code}" />{option.text}
		            </Label>
                          </FormGroup>

                      ))
                  }

		</Form>);
    }
}


// export default connect(....

