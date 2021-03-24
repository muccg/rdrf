import * as React from 'react';
import App from './index';

describe('An empty App', () => {
    // const newApp = <App />;
    // Constructed like this because of the way App is exported - the class is wrapped
    const newApp = new App.WrappedComponent({});
    it('is defined', () => {
        // stuff goes here
        expect(newApp).toBeDefined();
    });
    it('has empty properties', () => {
        expect(newApp).toHaveProperty('props');
        expect(newApp.props).toStrictEqual({});
    });
    it('does not have questions', () => {
        expect(newApp.props.questions).not.toBeDefined();
    });
    it('throws an error in atEnd', () => {
        expect(() => {
            newApp.atEnd();
        }).toThrow();
    });
    it('throws an error in getProgress', () => {
        expect(() => {
            newApp.getProgress();
        }).toThrow();
    });
    it('throws an error in movePrevious', () => {
        expect(() => {
            newApp.movePrevious();
        }).toThrow();
    });
    it('throws an error in moveNext', () => {
        expect(() => {
            newApp.moveNext();
        }).toThrow();
    });
    it('throws an error in render', () => {
        expect(() => {
            newApp.render();
        }).toThrow();
    });
    it('does not throw an error in atBeginning', () => {
        expect(() => {
            // atBeginning is interesting - doesn't throw an exception
            // No assignment of variables within the function
            // Only comparison between props.stage (which is undefined) and 0
            newApp.atBeginning();
            console.log(newApp.props.stage);
        }).not.toThrow();
    });
    it.todo('cannot render');
});