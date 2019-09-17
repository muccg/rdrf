import 'bootstrap/dist/css/bootstrap.min.css';

import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import { applyMiddleware, compose, createStore } from 'redux';
import thunk from 'redux-thunk';


import App from './app';
import { promsPageReducer } from './pages/proms_page/reducers';

const devtoolsExtension = '__REDUX_DEVTOOLS_EXTENSION_COMPOSE__';
const composeEnhancers = window[devtoolsExtension] || compose;

export const store = createStore(
    promsPageReducer,
    composeEnhancers(applyMiddleware(thunk))
);


const unsubscribe = store.subscribe(() => {})

ReactDOM.render(
    <Provider store={store}>
            <App />
    </Provider>,
    document.getElementById('app'));



