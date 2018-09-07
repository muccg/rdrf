import * as React from 'react';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';

import Instruction  from '../pages/proms_page/components/instruction';
import Question from '../pages/proms_page/components/question';
import { goPrevious, goNext } from '../pages/proms_page/reducers';

import { Button } from 'reactstrap';
import { Container, Row, Col } from 'reactstrap';

import { ElementList } from '../pages/proms_page/logic';

interface AppInterface {
    title: string,
    stage: number,
    questions: ElementList,
    goNext: any,
    goPrevious: any,
}


class App extends React.Component<AppInterface, object> {

    render() {
        return (

		<div className="App">
		
	          <Container>
                    <Row>
		     <Col>
		       <Instruction stage={this.props.stage} />
		     </Col>
                    </Row>
                    <Row>
		      <Col>
		<Question title={this.props.title} stage={this.props.stage} questions={this.props.questions}/>
		      </Col>
                    </Row>
		  </Container>
		<div className="footer">
		  <Row>
		    <Col>
		      <Button onClick={this.props.goPrevious} >Prev</Button>
		    </Col>
		    <Col>
		       <Button onClick={this.props.goNext}>Next</Button>
		    </Col>
		  </Row>
		</div>

		</div>

		        );
    }

}

function mapStateToProps(state) {
    return {stage: state.stage,
	    title: state.title,
	    questions: state.questions}
}

function mapDispatchToProps(dispatch) {
return bindActionCreators({
    goNext,
    goPrevious,
     }, dispatch);
}

export default connect(mapStateToProps,mapDispatchToProps)(App);
