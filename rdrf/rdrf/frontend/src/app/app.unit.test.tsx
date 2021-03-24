import * as React from 'react';
import App from './index';

describe('An empty App', () => {
    const newApp = <App />
    it('is defined', () => {
        // stuff goes here
        expect(newApp).toBeDefined();
    });
    it('has properties', () => {
        expect(newApp).toHaveProperty('props');
    });
    it('does not have questions', () => {
        expect(newApp.props.questions).not.toBeDefined();
    });
});