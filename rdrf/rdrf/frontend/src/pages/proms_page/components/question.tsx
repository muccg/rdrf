import * as React from 'react';
import { Form, FormGroup, Label, Input } from 'reactstrap';


export default class Question extends React.Component<any> {
    render() {

	return ( 
		  <Form>	 
                   <FormGroup tag="fieldset">
                <legend>Question {this.props.stage}</legend>
		 </FormGroup>

		 <FormGroup check>
		       <Label check>
	                  <Input type="radio" name="radio1" />Option one
		       </Label>
    
                     </FormGroup>
		 <FormGroup check>
		 <Label check>
	<Input type="radio" name="radio1" />{' '}
	Option two can be something else and selecting it will deselect option one
		 </Label>
    </FormGroup>
		 
    <FormGroup check disabled>
    <Label check>
	<Input type="radio" name="radio1" disabled />{' '}
	Option three is disabled
		 </Label>
    </FormGroup>

<FormGroup check>
    <Label check>
    <Input type="checkbox" />{' '}
    Check me out
    </Label>
</FormGroup>

		</Form>);
    }
}


