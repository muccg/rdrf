import * as React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { applyMiddleware, compose, createStore } from 'redux';
import thunk from 'redux-thunk';
import { promsPageReducer} from '../pages/proms_page/reducers'
import App from './index';

const devtoolsExtension = '__REDUX_DEVTOOLS_EXTENSION_COMPOSE__';
const composeEnhancers = window[devtoolsExtension] || compose;

const testStore = createStore(
    promsPageReducer,
    composeEnhancers(applyMiddleware(thunk))
);

const unsubscribe = testStore.subscribe(() =>
    global.console.log(testStore.getState())
)

describe('An empty App component', () => {
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
        }).not.toThrow();
    });
});

describe('A test App using Redux', () => {
    it('can render', () => {
        const { rerender, asFragment } = render(
            <Provider store={testStore}>
                <App />
            </Provider>
        );
    });
});