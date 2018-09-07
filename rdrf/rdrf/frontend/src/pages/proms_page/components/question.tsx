import * as React from 'react';
import * as _ from 'lodash';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import { Form, FormGroup, Label, Input } from 'reactstrap';
import { QuestionInterface } from './interfaces';


class Question extends React.Component<QuestionInterface, object> {
    constructor(props) {
      super(props);
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
	                      <Input type="radio" name="radio1" value="{option.code}" />{option.text}
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

export default connect<{},{},QuestionInterface>(mapStateToProps)(Question);

	

