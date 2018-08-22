import * as React from 'react';

export default class Question extends React.Component<any> {
    render() {
	return ( <div className="question">
		 Stage = "{this.props.stage}" 
		   Question should go here
		 </div>);
    };
}


