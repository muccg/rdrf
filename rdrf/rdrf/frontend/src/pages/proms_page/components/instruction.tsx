import * as React from 'react';

export default class Instruction extends React.Component<any> {
    public render() {
	return (<div className="instruction">
	        {this.props.instructions}
	        </div>);
    }
};

