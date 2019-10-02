import React from 'react';
import ReactDOM from 'react-dom';
import App from './app';
import './index.css';
import * as serviceWorker from './serviceWorker';

import { Provider } from 'react-redux';
import { applyMiddleware, compose, createStore } from 'redux';
import thunk from 'redux-thunk';
import { promsPageReducer } from './pages/proms_page/reducers';

import 'bootstrap/dist/css/bootstrap.min.css';

const devtoolsExtension = '__REDUX_DEVTOOLS_EXTENSION_COMPOSE__';
const composeEnhancers = window[devtoolsExtension] || compose;

export const store = createStore(
    promsPageReducer,
    composeEnhancers(applyMiddleware(thunk))
);

const unsubscribe = store.subscribe(() =>
    global.console.log(store.getState())
)

ReactDOM.render(<Provider store={store}>
    <App />
</Provider>, document.getElementById('root'));

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();


