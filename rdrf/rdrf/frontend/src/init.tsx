import 'bootstrap/dist/css/bootstrap.min.css';

import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import thunk from 'redux-thunk';
import { createStore, applyMiddleware, compose } from 'redux';

import App from './app';
import { promsPageReducer } from './pages/proms_page/reducers';

const composeEnhancers = window['__REDUX_DEVTOOLS_EXTENSION_COMPOSE__'] || compose;

export const store = createStore(
    promsPageReducer,
    composeEnhancers(applyMiddleware(thunk))
);


const unsubscribe = store.subscribe(() =>
  console.log(store.getState())
)

ReactDOM.render(
    <Provider store={store}>
            <App />
    </Provider>,
    document.getElementById('app'));



