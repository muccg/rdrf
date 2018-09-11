var rdrfts =
(window["webpackJsonprdrfts"] = window["webpackJsonprdrfts"] || []).push([["main"],{

/***/ "./src/app/index.tsx":
/*!***************************!*\
  !*** ./src/app/index.tsx ***!
  \***************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

var __extends = (this && this.__extends) || (function () {
    var extendStatics = Object.setPrototypeOf ||
        ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
        function (d, b) { for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p]; };
    return function (d, b) {
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
var React = __webpack_require__(/*! react */ "./node_modules/react/index.js");
var react_redux_1 = __webpack_require__(/*! react-redux */ "./node_modules/react-redux/es/index.js");
var redux_1 = __webpack_require__(/*! redux */ "./node_modules/redux/es/redux.js");
var instruction_1 = __webpack_require__(/*! ../pages/proms_page/components/instruction */ "./src/pages/proms_page/components/instruction.tsx");
var question_1 = __webpack_require__(/*! ../pages/proms_page/components/question */ "./src/pages/proms_page/components/question.tsx");
var reducers_1 = __webpack_require__(/*! ../pages/proms_page/reducers */ "./src/pages/proms_page/reducers/index.ts");
var reactstrap_1 = __webpack_require__(/*! reactstrap */ "./node_modules/reactstrap/dist/reactstrap.es.js");
var reactstrap_2 = __webpack_require__(/*! reactstrap */ "./node_modules/reactstrap/dist/reactstrap.es.js");
var App = /** @class */ (function (_super) {
    __extends(App, _super);
    function App() {
        return _super !== null && _super.apply(this, arguments) || this;
    }
    App.prototype.atEnd = function () {
        var lastIndex = this.props.questions.length - 1;
        console.log("lastIndex = " + lastIndex.toString());
        console.log("stage = " + this.props.stage.toString());
        return this.props.stage == lastIndex;
    };
    App.prototype.render = function () {
        var nextButton;
        if (this.atEnd()) {
            console.log("at end");
            nextButton = (React.createElement(reactstrap_1.Button, { onClick: this.props.submitAnswers }, "Submit Answers"));
        }
        else {
            console.log("not at end");
            nextButton = (React.createElement(reactstrap_1.Button, { onClick: this.props.goNext }, "Next"));
        }
        ;
        return (React.createElement("div", { className: "App" },
            React.createElement(reactstrap_2.Container, null,
                React.createElement(reactstrap_2.Row, null,
                    React.createElement(reactstrap_2.Col, null,
                        React.createElement(instruction_1.default, { stage: this.props.stage }))),
                React.createElement(reactstrap_2.Row, null,
                    React.createElement(reactstrap_2.Col, null,
                        React.createElement(question_1.default, { title: this.props.title, stage: this.props.stage, questions: this.props.questions }))),
                React.createElement(reactstrap_2.Row, null,
                    React.createElement(reactstrap_2.Col, null,
                        React.createElement(reactstrap_1.Button, { onClick: this.props.goPrevious }, "Prev")),
                    React.createElement(reactstrap_2.Col, null, nextButton)))));
    };
    return App;
}(React.Component));
function mapStateToProps(state) {
    return { stage: state.stage,
        title: state.title,
        questions: state.questions };
}
function mapDispatchToProps(dispatch) {
    return redux_1.bindActionCreators({
        goNext: reducers_1.goNext,
        goPrevious: reducers_1.goPrevious,
        submitAnswers: reducers_1.submitAnswers,
    }, dispatch);
}
exports.default = react_redux_1.connect(mapStateToProps, mapDispatchToProps)(App);


/***/ }),

/***/ "./src/init.tsx":
/*!**********************!*\
  !*** ./src/init.tsx ***!
  \**********************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

Object.defineProperty(exports, "__esModule", { value: true });
__webpack_require__(/*! bootstrap/dist/css/bootstrap.min.css */ "./node_modules/bootstrap/dist/css/bootstrap.min.css");
var React = __webpack_require__(/*! react */ "./node_modules/react/index.js");
var ReactDOM = __webpack_require__(/*! react-dom */ "./node_modules/react-dom/index.js");
var react_redux_1 = __webpack_require__(/*! react-redux */ "./node_modules/react-redux/es/index.js");
var redux_thunk_1 = __webpack_require__(/*! redux-thunk */ "./node_modules/redux-thunk/es/index.js");
var redux_1 = __webpack_require__(/*! redux */ "./node_modules/redux/es/redux.js");
var app_1 = __webpack_require__(/*! ./app */ "./src/app/index.tsx");
var reducers_1 = __webpack_require__(/*! ./pages/proms_page/reducers */ "./src/pages/proms_page/reducers/index.ts");
var composeEnhancers = window['__REDUX_DEVTOOLS_EXTENSION_COMPOSE__'] || redux_1.compose;
exports.store = redux_1.createStore(reducers_1.promsPageReducer, composeEnhancers(redux_1.applyMiddleware(redux_thunk_1.default)));
var unsubscribe = exports.store.subscribe(function () {
    return console.log(exports.store.getState());
});
ReactDOM.render(React.createElement(react_redux_1.Provider, { store: exports.store },
    React.createElement(app_1.default, null)), document.getElementById('app'));


/***/ }),

/***/ "./src/pages/proms_page/components/instruction.tsx":
/*!*********************************************************!*\
  !*** ./src/pages/proms_page/components/instruction.tsx ***!
  \*********************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

var __extends = (this && this.__extends) || (function () {
    var extendStatics = Object.setPrototypeOf ||
        ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
        function (d, b) { for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p]; };
    return function (d, b) {
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
var React = __webpack_require__(/*! react */ "./node_modules/react/index.js");
var Instruction = /** @class */ (function (_super) {
    __extends(Instruction, _super);
    function Instruction() {
        return _super !== null && _super.apply(this, arguments) || this;
    }
    Instruction.prototype.render = function () {
        return (React.createElement("div", { className: "instruction" }, this.props.instructions));
    };
    return Instruction;
}(React.Component));
exports.default = Instruction;
;


/***/ }),

/***/ "./src/pages/proms_page/components/question.tsx":
/*!******************************************************!*\
  !*** ./src/pages/proms_page/components/question.tsx ***!
  \******************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

var __extends = (this && this.__extends) || (function () {
    var extendStatics = Object.setPrototypeOf ||
        ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
        function (d, b) { for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p]; };
    return function (d, b) {
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
var React = __webpack_require__(/*! react */ "./node_modules/react/index.js");
var _ = __webpack_require__(/*! lodash */ "./node_modules/lodash/lodash.js");
var react_redux_1 = __webpack_require__(/*! react-redux */ "./node_modules/react-redux/es/index.js");
var reactstrap_1 = __webpack_require__(/*! reactstrap */ "./node_modules/reactstrap/dist/reactstrap.es.js");
var actions = __webpack_require__(/*! ../reducers */ "./src/pages/proms_page/reducers/index.ts");
var Question = /** @class */ (function (_super) {
    __extends(Question, _super);
    function Question(props) {
        return _super.call(this, props) || this;
    }
    Question.prototype.handleChange = function (event) {
        console.log("radio button clicked");
        console.log(event);
        var cdeValue = event.target.value;
        var cdeCode = event.target.name;
        console.log("cde = " + cdeCode.toString());
        console.log("value = " + cdeValue.toString());
        this.props.enterData(cdeCode, cdeValue);
    };
    Question.prototype.render = function () {
        var _this = this;
        var question = this.props.questions[this.props.stage];
        return (React.createElement(reactstrap_1.Form, null,
            React.createElement(reactstrap_1.FormGroup, { tag: "fieldset" },
                React.createElement("legend", null, this.props.questions[this.props.stage].title)),
            _.map(question.options, function (option, index) { return (React.createElement(reactstrap_1.FormGroup, { check: true },
                React.createElement(reactstrap_1.Label, { check: true },
                    React.createElement(reactstrap_1.Input, { type: "radio", name: _this.props.questions[_this.props.stage].cde, value: option.code, onChange: _this.handleChange.bind(_this), checked: option.code === _this.props.answers[question.cde] }),
                    option.text))); })));
    };
    return Question;
}(React.Component));
function mapStateToProps(state) {
    return { questions: state.questions,
        stage: state.stage,
        answers: state.answers,
    };
}
function mapPropsToDispatch(dispatch) {
    return ({
        enterData: function (cdeCode, cdeValue) { return dispatch(actions.enterData({ cde: cdeCode, value: cdeValue })); },
    });
}
exports.default = react_redux_1.connect(mapStateToProps, mapPropsToDispatch)(Question);


/***/ }),

/***/ "./src/pages/proms_page/logic.ts":
/*!***************************************!*\
  !*** ./src/pages/proms_page/logic.ts ***!
  \***************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

Object.defineProperty(exports, "__esModule", { value: true });
function evalCondition(cond, state) {
    // Evaluates a conditional element in the current state
    // We only show applicable questions - i.e. those
    // which evaluate to true
    if (state.answers.hasOwnProperty(cond.cde)) {
        var answer = state.answers[cond.cde];
        switch (cond.op) {
            case '=':
                return answer == cond.value;
            default:
                return false; // extend this later
        }
    }
    else {
        return false;
    }
}
function evalElement(el, state) {
    switch (el.tag) {
        case 'cde':
            // Unconditional elements are always shown
            return true;
        case 'cond':
            // conditional elements depend their associated
            // condition being true
            return evalCondition(el.cond, state);
        default:
            return false;
    }
}
function evalElements(elements, state) {
    // The questions to show at any time are those whose preconditions
    // are fulfilled
    return elements.filter(function (el) { return evalElement(el, state); });
}
exports.evalElements = evalElements;


/***/ }),

/***/ "./src/pages/proms_page/reducers/index.ts":
/*!************************************************!*\
  !*** ./src/pages/proms_page/reducers/index.ts ***!
  \************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

var __assign = (this && this.__assign) || Object.assign || function(t) {
    for (var s, i = 1, n = arguments.length; i < n; i++) {
        s = arguments[i];
        for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
            t[p] = s[p];
    }
    return t;
};
Object.defineProperty(exports, "__esModule", { value: true });
var redux_actions_1 = __webpack_require__(/*! redux-actions */ "./node_modules/redux-actions/es/index.js");
exports.goPrevious = redux_actions_1.createAction("PROMS_PREVIOUS");
exports.goNext = redux_actions_1.createAction("PROMS_NEXT");
exports.submitAnswers = redux_actions_1.createAction("PROMS_SUBMIT");
exports.enterData = redux_actions_1.createAction("PROMS_ENTER_DATA");
var logic_1 = __webpack_require__(/*! ../logic */ "./src/pages/proms_page/logic.ts");
var axios_1 = __webpack_require__(/*! axios */ "./node_modules/axios/index.js");
axios_1.default.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios_1.default.defaults.xsrfCookieName = "csrftoken";
function submitSurvey(answers) {
    var patientToken = window.proms_config.patient_token;
    var registryCode = window.proms_config.registry_code;
    var surveyName = window.proms_config.survey_name;
    var surveyEndpoint = window.proms_config.survey_endpoint;
    var data = { patient_token: patientToken,
        registry_code: registryCode,
        survey_name: surveyName,
        answers: answers };
    axios_1.default.post(surveyEndpoint, data)
        .then(function (res) { return window.location.replace(window.proms_config.completed_page); })
        .catch(function (err) { return alert(err.toString()); });
}
var initialState = {
    stage: 0,
    answers: {},
    questions: logic_1.evalElements(window.proms_config.questions, { answers: {} }),
    title: '',
};
function isCond(state) {
    var stage = state.stage;
    return state.questions[stage].tag == 'cond';
}
function updateAnswers(action, state) {
    // if data entered , update the answers object
    var cdeCode = action.payload.cde;
    var newValue = action.payload.value;
    var oldAnswers = state.answers;
    var newAnswers = __assign({}, oldAnswers);
    newAnswers[cdeCode] = newValue;
    return newAnswers;
}
exports.promsPageReducer = redux_actions_1.handleActions((_a = {},
    _a[exports.goPrevious] = function (state, action) { return (__assign({}, state, { stage: state.stage - 1 })); },
    _a[exports.goNext] = function (state, action) { return (__assign({}, state, { stage: state.stage + 1 })); },
    _a[exports.submitAnswers] = function (state, action) {
        console.log("submitting answers");
        submitSurvey(state.answers);
        return state;
    },
    _a[exports.enterData] = function (state, action) {
        console.log("enterData action received");
        console.log("action = " + action.toString());
        console.log("answers before update = " + state.answers.toString());
        var updatedAnswers = updateAnswers(action, state);
        console.log("updated answers = " + updatedAnswers.toString());
        var newState = __assign({}, state, { answers: updateAnswers(action, state), questions: logic_1.evalElements(window.proms_config.questions, { answers: updatedAnswers }) });
        console.log("newState = " + newState.toString());
        return newState;
    },
    _a), initialState);
var _a;


/***/ })

},[["./src/init.tsx","runtime","vendors"]]]);
//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly9yZHJmdHMvLi9zcmMvYXBwL2luZGV4LnRzeCIsIndlYnBhY2s6Ly9yZHJmdHMvLi9zcmMvaW5pdC50c3giLCJ3ZWJwYWNrOi8vcmRyZnRzLy4vc3JjL3BhZ2VzL3Byb21zX3BhZ2UvY29tcG9uZW50cy9pbnN0cnVjdGlvbi50c3giLCJ3ZWJwYWNrOi8vcmRyZnRzLy4vc3JjL3BhZ2VzL3Byb21zX3BhZ2UvY29tcG9uZW50cy9xdWVzdGlvbi50c3giLCJ3ZWJwYWNrOi8vcmRyZnRzLy4vc3JjL3BhZ2VzL3Byb21zX3BhZ2UvbG9naWMudHMiLCJ3ZWJwYWNrOi8vcmRyZnRzLy4vc3JjL3BhZ2VzL3Byb21zX3BhZ2UvcmVkdWNlcnMvaW5kZXgudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFBQSw4RUFBK0I7QUFDL0IscUdBQXNDO0FBQ3RDLG1GQUEyQztBQUUzQywrSUFBc0U7QUFDdEUsc0lBQStEO0FBQy9ELHFIQUFpRjtBQUVqRiw0R0FBb0M7QUFDcEMsNEdBQWlEO0FBY2pEO0lBQWtCLHVCQUFxQztJQUF2RDs7SUFpREEsQ0FBQztJQWhERyxtQkFBSyxHQUFMO1FBQ0gsSUFBSSxTQUFTLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxTQUFTLENBQUMsTUFBTSxHQUFHLENBQUMsQ0FBQztRQUNoRCxPQUFPLENBQUMsR0FBRyxDQUFDLGNBQWMsR0FBRyxTQUFTLENBQUMsUUFBUSxFQUFFLENBQUMsQ0FBQztRQUNuRCxPQUFPLENBQUMsR0FBRyxDQUFDLFVBQVUsR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLEtBQUssQ0FBQyxRQUFRLEVBQUUsQ0FBQyxDQUFDO1FBQ3RELE9BQU8sSUFBSSxDQUFDLEtBQUssQ0FBQyxLQUFLLElBQUksU0FBUyxDQUFDO0lBQ2xDLENBQUM7SUFFRCxvQkFBTSxHQUFOO1FBQ0gsSUFBSSxVQUFVLENBQUM7UUFDZixJQUFHLElBQUksQ0FBQyxLQUFLLEVBQUUsRUFB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R0FBQyxxQkFBb0IsSUFDckIsVUFBQyxLQUFLLEVBQUUsTUFBVztRQUN0QixPQUFPLENBQUMsR0FBRyxDQUFDLG9CQUFvQixDQUFDLENBQUM7UUFDbEMsWUFBWSxDQUFDLEtBQUssQ0FBQyxPQUFPLENBQUMsQ0FBQztRQUM1QixPQUFPLEtBQUssQ0FBQztJQUNWLENBQUM7SUFDRCxHQUFDLGlCQUFnQixJQUNqQixVQUFDLEtBQUssRUFBRSxNQUFNO1FBQ2pCLE9BQU8sQ0FBQyxHQUFHLENBQUMsMkJBQTJCLENBQUMsQ0FBQztRQUN6QyxPQUFPLENBQUMsR0FBRyxDQUFDLFdBQVcsR0FBRyxNQUFNLENBQUMsUUFBUSxFQUFFLENBQUMsQ0FBQztRQUM3QyxPQUFPLENBQUMsR0FBRyxDQUFDLDBCQUEwQixHQUFHLEtBQUssQ0FBQyxPQUFPLENBQUMsUUFBUSxFQUFFLENBQUMsQ0FBQztRQUNuRSxJQUFJLGNBQWMsR0FBRyxhQUFhLENBQUMsTUFBTSxFQUFFLEtBQUssQ0FBQztRQUNqRCxPQUFPLENBQUMsR0FBRyxDQUFDLG9CQUFvQixHQUFHLGNBQWMsQ0FBQyxRQUFRLEVBQUUsQ0FBQyxDQUFDO1FBQzlELElBQUksUUFBUSxnQkFDTCxLQUFLLElBQ1IsT0FBTyxFQUFFLGFBQWEsQ0FBQyxNQUFNLEVBQUUsS0FBSyxDQUFDLEVBQ3JDLFNBQVMsRUFBRSxvQkFBWSxDQUFDLE1BQU0sQ0FBQyxZQUFZLENBQUMsU0FBUyxFQUFDLEVBQUMsT0FBTyxFQUFFLGNBQWMsRUFBQyxDQUFDLEdBQ25GLENBQUM7UUFDRixPQUFPLENBQUMsR0FBRyxDQUFDLGFBQWEsR0FBRyxRQUFRLENBQUMsUUFBUSxFQUFFLENBQUMsQ0FBQztRQUNqRCxPQUFPLFFBQVEsQ0FBQztJQUNiLENBQUM7U0FDRixZQUFZLENBQUMsQ0FBQyIsImZpbGUiOiJtYWluLWJ1bmRsZS5qcyIsInNvdXJjZXNDb250ZW50IjpbImltcG9ydCAqIGFzIFJlYWN0IGZyb20gJ3JlYWN0JztcbmltcG9ydCB7IGNvbm5lY3QgfSBmcm9tICdyZWFjdC1yZWR1eCc7XG5pbXBvcnQgeyBiaW5kQWN0aW9uQ3JlYXRvcnMgfSBmcm9tICdyZWR1eCc7XG5cbmltcG9ydCBJbnN0cnVjdGlvbiAgZnJvbSAnLi4vcGFnZXMvcHJvbXNfcGFnZS9jb21wb25lbnRzL2luc3RydWN0aW9uJztcbmltcG9ydCBRdWVzdGlvbiBmcm9tICcuLi9wYWdlcy9wcm9tc19wYWdlL2NvbXBvbmVudHMvcXVlc3Rpb24nO1xuaW1wb3J0IHsgZ29QcmV2aW91cywgZ29OZXh0LCBzdWJtaXRBbnN3ZXJzIH0gZnJvbSAnLi4vcGFnZXMvcHJvbXNfcGFnZS9yZWR1Y2Vycyc7XG5cbmltcG9ydCB7IEJ1dHRvbiB9IGZyb20gJ3JlYWN0c3RyYXAnO1xuaW1wb3J0IHsgQ29udGFpbmVyLCBSb3csIENvbCB9IGZyb20gJ3JlYWN0c3RyYXAnO1xuXG5pbXBvcnQgeyBFbGVtZW50TGlzdCB9IGZyb20gJy4uL3BhZ2VzL3Byb21zX3BhZ2UvbG9naWMnO1xuXG5pbnRlcmZhY2UgQXBwSW50ZXJmYWNlIHtcbiAgICB0aXRsZTogc3RyaW5nLFxuICAgIHN0YWdlOiBudW1iZXIsXG4gICAgcXVlc3Rpb25zOiBFbGVtZW50TGlzdCxcbiAgICBnb05leHQ6IGFueSxcbiAgICBnb1ByZXZpb3VzOiBhbnksXG4gICAgc3VibWl0QW5zd2VyczogYW55LFxufVxuXG5cbmNsYXNzIEFwcCBleHRlbmRzIFJlYWN0LkNvbXBvbmVudDxBcHBJbnRlcmZhY2UsIG9iamVjdD4ge1xuICAgIGF0RW5kKCkge1xuXHRsZXQgbGFzdEluZGV4ID0gdGhpcy5wcm9wcy5xdWVzdGlvbnMubGVuZ3RoIC0gMTtcblx0Y29uc29sZS5sb2coXCJsYXN0SW5kZXggPSBcIiArIGxhc3RJbmRleC50b1N0cmluZygpKTtcblx0Y29uc29sZS5sb2coXCJzdGFnZSA9IFwiICsgdGhpcy5wcm9wcy5zdGFnZS50b1N0cmluZygpKTtcblx0cmV0dXJuIHRoaXMucHJvcHMuc3RhZ2UgPT0gbGFzdEluZGV4O1xuICAgIH1cblxuICAgIHJlbmRlcigpIHtcblx0dmFyIG5leHRCdXR0b247XG5cdGlmKHRoaXMuYXRFbmQoKSkge1xuXHQgICAgY29uc29sZS5sb2coXCJhdCBlbmRcIik7XG5cdCAgICBuZXh0QnV0dG9uID0gKDxCdXR0b24gb25DbGljaz17dGhpcy5wcm9wcy5zdWJtaXRBbnN3ZXJzfT5TdWJtaXQgQW5zd2VyczwvQnV0dG9uPik7XG5cdH1cblx0ZWxzZSB7XG5cdCAgICBjb25zb2xlLmxvZyhcIm5vdCBhdCBlbmRcIik7IFxuXHQgICAgbmV4dEJ1dHRvbiA9ICg8QnV0dG9uIG9uQ2xpY2s9e3RoaXMucHJvcHMuZ29OZXh0fT5OZXh0PC9CdXR0b24+KTtcblx0fTtcblx0XG4gICAgICAgIHJldHVybiAoXG5cblx0XHQ8ZGl2IGNsYXNzTmFtZT1cIkFwcFwiPlxuXHQgICAgICAgICAgPENvbnRhaW5lcj5cbiAgICAgICAgICAgICAgICAgICAgPFJvdz5cblx0XHQgICAgIDxDb2w+XG5cdFx0ICAgICAgIDxJbnN0cnVjdGlvbiBzdGFnZT17dGhpcy5wcm9wcy5zdGFnZX0gLz5cblx0XHQgICAgIDwvQ29sPlxuICAgICAgICAgICAgICAgICAgICA8L1Jvdz5cblxuICAgICAgICAgICAgICAgICAgICA8Um93PlxuXHRcdCAgICAgIDxDb2w+XG5cdFx0ICAgICAgIDxRdWVzdGlvbiB0aXRsZT17dGhpcy5wcm9wcy50aXRsZX0gc3RhZ2U9e3RoaXMucHJvcHMuc3RhZ2V9IHF1ZXN0aW9ucz17dGhpcy5wcm9wcy5xdWVzdGlvbnN9Lz5cblx0XHQgICAgICA8L0NvbD5cbiAgICAgICAgICAgICAgICAgICAgPC9Sb3c+XG5cblx0XHQgIDxSb3c+XG5cdFx0ICAgIDxDb2w+XG5cdFx0ICAgICAgPEJ1dHRvbiBvbkNsaWNrPXt0aGlzLnByb3BzLmdvUHJldmlvdXN9ID5QcmV2PC9CdXR0b24+XG5cdFx0ICAgIDwvQ29sPlxuXHRcdCAgICA8Q29sPlxuXHRcdCAgICAgIHtuZXh0QnV0dG9ufVxuXHRcdCAgICA8L0NvbD5cblx0XHQgIDwvUm93PlxuXHRcdDwvQ29udGFpbmVyPlxuXHRcdDwvZGl2PlxuXG5cdFx0ICAgICAgICApO1xuICAgIH1cblxufVxuXG5mdW5jdGlvbiBtYXBTdGF0ZVRvUHJvcHMoc3RhdGUpIHtcbiAgICByZXR1cm4ge3N0YWdlOiBzdGF0ZS5zdGFnZSxcblx0ICAgIHRpdGxlOiBzdGF0ZS50aXRsZSxcblx0ICAgIHF1ZXN0aW9uczogc3RhdGUucXVlc3Rpb25zfVxufVxuXG5mdW5jdGlvbiBtYXBEaXNwYXRjaFRvUHJvcHMoZGlzcGF0Y2gpIHtcbnJldHVybiBiaW5kQWN0aW9uQ3JlYXRvcnMoe1xuICAgIGdvTmV4dCxcbiAgICBnb1ByZXZpb3VzLFxuICAgIHN1Ym1pdEFuc3dlcnMsXG4gICAgIH0sIGRpc3BhdGNoKTtcbn1cblxuZXhwb3J0IGRlZmF1bHQgY29ubmVjdChtYXBTdGF0ZVRvUHJvcHMsbWFwRGlzcGF0Y2hUb1Byb3BzKShBcHApO1xuIiwiaW1wb3J0ICdib290c3RyYXAvZGlzdC9jc3MvYm9vdHN0cmFwLm1pbi5jc3MnO1xuXG5pbXBvcnQgKiBhcyBSZWFjdCBmcm9tICdyZWFjdCc7XG5pbXBvcnQgKiBhcyBSZWFjdERPTSBmcm9tICdyZWFjdC1kb20nO1xuaW1wb3J0IHsgUHJvdmlkZXIgfSBmcm9tICdyZWFjdC1yZWR1eCc7XG5pbXBvcnQgdGh1bmsgZnJvbSAncmVkdXgtdGh1bmsnO1xuaW1wb3J0IHsgY3JlYXRlU3RvcmUsIGFwcGx5TWlkZGxld2FyZSwgY29tcG9zZSB9IGZyb20gJ3JlZHV4JztcblxuaW1wb3J0IEFwcCBmcm9tICcuL2FwcCc7XG5pbXBvcnQgeyBwcm9tc1BhZ2VSZWR1Y2VyIH0gZnJvbSAnLi9wYWdlcy9wcm9tc19wYWdlL3JlZHVjZXJzJztcblxuY29uc3QgY29tcG9zZUVuaGFuY2VycyA9IHdpbmRvd1snX19SRURVWF9ERVZUT09MU19FWFRFTlNJT05fQ09NUE9TRV9fJ10gfHwgY29tcG9zZTtcblxuZXhwb3J0IGNvbnN0IHN0b3JlID0gY3JlYXRlU3RvcmUoXG4gICAgcHJvbXNQYWdlUmVkdWNlcixcbiAgICBjb21wb3NlRW5oYW5jZXJzKGFwcGx5TWlkZGxld2FyZSh0aHVuaykpXG4pO1xuXG5cbmNvbnN0IHVuc3Vic2NyaWJlID0gc3RvcmUuc3Vic2NyaWJlKCgpID0+XG4gIGNvbnNvbGUubG9nKHN0b3JlLmdldFN0YXRlKCkpXG4pXG5cblJlYWN0RE9NLnJlbmRlcihcbiAgICA8UHJvdmlkZXIgc3RvcmU9e3N0b3JlfT5cbiAgICAgICAgICAgIDxBcHAgLz5cbiAgICA8L1Byb3ZpZGVyPixcbiAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnYXBwJykpO1xuXG5cblxuIiwiaW1wb3J0ICogYXMgUmVhY3QgZnJvbSAncmVhY3QnO1xuXG5leHBvcnQgZGVmYXVsdCBjbGFzcyBJbnN0cnVjdGlvbiBleHRlbmRzIFJlYWN0LkNvbXBvbmVudDxhbnk+IHtcbiAgICByZW5kZXIoKSB7XG5cdHJldHVybiAoPGRpdiBjbGFzc05hbWU9XCJpbnN0cnVjdGlvblwiPlxuXHQgICAgICAgIHt0aGlzLnByb3BzLmluc3RydWN0aW9uc31cblx0ICAgICAgICA8L2Rpdj4pO1xuICAgIH1cbn07XG5cbiIsImltcG9ydCAqIGFzIFJlYWN0IGZyb20gJ3JlYWN0JztcbmltcG9ydCAqIGFzIF8gZnJvbSAnbG9kYXNoJztcbmltcG9ydCB7IGNvbm5lY3QgfSBmcm9tICdyZWFjdC1yZWR1eCc7XG5pbXBvcnQgeyBiaW5kQWN0aW9uQ3JlYXRvcnMgfSBmcm9tICdyZWR1eCc7XG5cbmltcG9ydCB7IEJ1dHRvbiwgRm9ybSwgRm9ybUdyb3VwLCBMYWJlbCwgSW5wdXQgfSBmcm9tICdyZWFjdHN0cmFwJztcbmltcG9ydCB7IFF1ZXN0aW9uSW50ZXJmYWNlIH0gZnJvbSAnLi9pbnRlcmZhY2VzJztcblxuaW1wb3J0ICogYXMgYWN0aW9ucyBmcm9tICcuLi9yZWR1Y2Vycyc7XG5cblxuXG5jbGFzcyBRdWVzdGlvbiBleHRlbmRzIFJlYWN0LkNvbXBvbmVudDxRdWVzdGlvbkludGVyZmFjZSwgb2JqZWN0PiB7XG4gICAgY29uc3RydWN0b3IocHJvcHMpIHtcbiAgICAgIHN1cGVyKHByb3BzKTtcbiAgICB9XG5cbiAgICBoYW5kbGVDaGFuZ2UoZXZlbnQpIHtcblx0Y29uc29sZS5sb2coXCJyYWRpbyBidXR0b24gY2xpY2tlZFwiKTtcblx0Y29uc29sZS5sb2coZXZlbnQpO1xuXHRsZXQgY2RlVmFsdWUgID0gZXZlbnQudGFyZ2V0LnZhbHVlO1xuXHRsZXQgY2RlQ29kZSA9IGV2ZW50LnRhcmdldC5uYW1lO1xuXHRjb25zb2xlLmxvZyhcImNkZSA9IFwiICsgY2RlQ29kZS50b1N0cmluZygpKTtcblx0Y29uc29sZS5sb2coXCJ2YWx1ZSA9IFwiICsgY2RlVmFsdWUudG9TdHJpbmcoKSk7XG5cdHRoaXMucHJvcHMuZW50ZXJEYXRhKGNkZUNvZGUsIGNkZVZhbHVlKTtcbiAgICB9XG5cbiAgICByZW5kZXIoKSB7XG5cdGxldCBxdWVzdGlvbiA9IHRoaXMucHJvcHMucXVlc3Rpb25zW3RoaXMucHJvcHMuc3RhZ2VdO1xuXHRyZXR1cm4gKCBcblx0XHQ8Rm9ybT5cdCBcbiAgICAgICAgICAgICAgICAgICA8Rm9ybUdyb3VwIHRhZz1cImZpZWxkc2V0XCI+XG4gICAgICAgICAgICAgICAgPGxlZ2VuZD57dGhpcy5wcm9wcy5xdWVzdGlvbnNbdGhpcy5wcm9wcy5zdGFnZV0udGl0bGV9PC9sZWdlbmQ+XG5cdFx0ICAgPC9Gb3JtR3JvdXA+XG5cblx0XHQgIHtcbiAgICAgICAgICAgICAgICAgICAgICBfLm1hcChxdWVzdGlvbi5vcHRpb25zLCAob3B0aW9uLCBpbmRleCkgPT4gKFxuXHRcdCAgICAgICAgICA8Rm9ybUdyb3VwIGNoZWNrPlxuXHRcdCAgICAgICAgICAgIDxMYWJlbCBjaGVjaz5cblx0ICAgICAgICAgICAgICAgICAgICA8SW5wdXQgdHlwZT1cInJhZGlvXCIgbmFtZT17dGhpcy5wcm9wcy5xdWVzdGlvbnNbdGhpcy5wcm9wcy5zdGFnZV0uY2RlfSB2YWx1ZT17b3B0aW9uLmNvZGV9XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlPXt0aGlzLmhhbmRsZUNoYW5nZS5iaW5kKHRoaXMpfVxuXHRcdFx0ICAgICAgICAgICBjaGVja2VkPXtvcHRpb24uY29kZSA9PT0gdGhpcy5wcm9wcy5hbnN3ZXJzW3F1ZXN0aW9uLmNkZV19Lz57b3B0aW9uLnRleHR9XG5cdFx0ICAgICAgICAgICAgPC9MYWJlbD5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgPC9Gb3JtR3JvdXA+XG4gICAgICAgICAgICAgICAgICAgICAgKSlcbiAgICAgICAgICAgICAgICAgIH1cblxuXHRcdDwvRm9ybT4pO1xuICAgIH1cbn1cblxuZnVuY3Rpb24gbWFwU3RhdGVUb1Byb3BzKHN0YXRlKSB7XG4gICAgcmV0dXJuIHtxdWVzdGlvbnM6IHN0YXRlLnF1ZXN0aW9ucyxcblx0ICAgIHN0YWdlOiBzdGF0ZS5zdGFnZSxcblx0ICAgIGFuc3dlcnM6IHN0YXRlLmFuc3dlcnMsXG5cdCAgIH07XG59XG5cbmZ1bmN0aW9uIG1hcFByb3BzVG9EaXNwYXRjaChkaXNwYXRjaCkge1xuICAgIHJldHVybiAoe1xuXHRlbnRlckRhdGE6IChjZGVDb2RlOnN0cmluZywgY2RlVmFsdWU6IGFueSkgPT4gZGlzcGF0Y2goYWN0aW9ucy5lbnRlckRhdGEoe2NkZTpjZGVDb2RlLCB2YWx1ZTpjZGVWYWx1ZX0pKSxcbiAgICB9KTtcbn1cblxuZXhwb3J0IGRlZmF1bHQgY29ubmVjdDx7fSx7fSxRdWVzdGlvbkludGVyZmFjZT4obWFwU3RhdGVUb1Byb3BzLCBtYXBQcm9wc1RvRGlzcGF0Y2gpKFF1ZXN0aW9uKTtcblxuXHRcblxuIiwiaW1wb3J0ICogYXMgXyBmcm9tICdsb2Rhc2gnO1xuXG5pbnRlcmZhY2UgRXF1YWxzQ29uZGl0aW9uIHtcbiAgICBvcDogJz0nLFxuICAgIGNkZTogc3RyaW5nLFxuICAgIHZhbHVlOiBhbnksXG59XG5cbi8vIG1heWJlIHRoaXMgaXMgZW5vdWdoXG50eXBlIENvbmRpdGlvbiA9IEVxdWFsc0NvbmRpdGlvbjtcblxuLy8gRWxlbWVudHMgb2Ygd29ya2Zsb3dcbi8vIEkgdHJpZWQgdG8gbWFrZSBVbmNvbmRpdGlvbmFsRWxlbWVudCBqdXN0IGEgc3RyaW5nIGJ1dCBnb3QgdHlwZSBlcnJvcnNcbmludGVyZmFjZSBPcHRpb24ge1xuICAgIGNvZGU6IHN0cmluZyxcbiAgICB0ZXh0OiBzdHJpbmcsXG59XG5cbmludGVyZmFjZSBVbmNvbmRpdGlvbmFsRWxlbWVudCAge1xuICAgIHRhZzogJ2NkZScsXG4gICAgY2RlOiBzdHJpbmcsXG4gICAgdGl0bGU6IHN0cmluZyxcbiAgICBvcHRpb25zOiBbT3B0aW9uXSxcbn1cblxuaW50ZXJmYWNlIENvbmRpdGlvbmFsRWxlbWVudCB7XG4gICAgdGFnOiAnY29uZCcsXG4gICAgY29uZDogQ29uZGl0aW9uLFxuICAgIGNkZTogc3RyaW5nLFxuICAgIHRpdGxlOiBzdHJpbmcsXG4gICAgb3B0aW9uczogW09wdGlvbl0sXG59XG5cbnR5cGUgRWxlbWVudCA9IFVuY29uZGl0aW9uYWxFbGVtZW50IHwgQ29uZGl0aW9uYWxFbGVtZW50O1xuXG5leHBvcnQgdHlwZSBFbGVtZW50TGlzdCA9IFtFbGVtZW50XTtcblxuZnVuY3Rpb24gZXZhbENvbmRpdGlvbihjb25kOiBDb25kaXRpb24sIHN0YXRlOiBhbnkpOiBib29sZWFuIHtcbiAgICAvLyBFdmFsdWF0ZXMgYSBjb25kaXRpb25hbCBlbGVtZW50IGluIHRoZSBjdXJyZW50IHN0YXRlXG4gICAgLy8gV2Ugb25seSBzaG93IGFwcGxpY2FibGUgcXVlc3Rpb25zIC0gaS5lLiB0aG9zZVxuICAgIC8vIHdoaWNoIGV2YWx1YXRlIHRvIHRydWVcbiAgICBpZiAoc3RhdGUuYW5zd2Vycy5oYXNPd25Qcm9wZXJ0eShjb25kLmNkZSkpIHtcblx0bGV0IGFuc3dlciA9IHN0YXRlLmFuc3dlcnNbY29uZC5jZGVdO1xuXHRzd2l0Y2ggKGNvbmQub3ApIHtcblx0ICAgIGNhc2UgJz0nOlxuXHRcdHJldHVybiBhbnN3ZXIgPT0gY29uZC52YWx1ZTtcbiAgICAgICAgICAgIGRlZmF1bHQ6XG5cdFx0cmV0dXJuIGZhbHNlOyAvLyBleHRlbmQgdGhpcyBsYXRlclxuXHR9XG4gICAgfVxuICAgIGVsc2Uge1xuXHRyZXR1cm4gZmFsc2U7XG4gICAgfVxufVxuICAgIFxuXG5mdW5jdGlvbiBldmFsRWxlbWVudChlbDpFbGVtZW50LCBzdGF0ZTogYW55KTogYm9vbGVhbiB7XG4gICAgc3dpdGNoKGVsLnRhZykge1xuXHRjYXNlICdjZGUnOlxuXHQgICAgLy8gVW5jb25kaXRpb25hbCBlbGVtZW50cyBhcmUgYWx3YXlzIHNob3duXG5cdCAgICByZXR1cm4gdHJ1ZTtcblx0Y2FzZSAnY29uZCc6XG5cdCAgICAvLyBjb25kaXRpb25hbCBlbGVtZW50cyBkZXBlbmQgdGhlaXIgYXNzb2NpYXRlZFxuXHQgICAgLy8gY29uZGl0aW9uIGJlaW5nIHRydWVcblx0ICAgIHJldHVybiBldmFsQ29uZGl0aW9uKGVsLmNvbmQsIHN0YXRlKTtcblx0ZGVmYXVsdDpcblx0ICAgIHJldHVybiBmYWxzZTtcbiAgICB9XG59XG5cblxuZXhwb3J0IGZ1bmN0aW9uIGV2YWxFbGVtZW50cyhlbGVtZW50czogRWxlbWVudFtdLCBzdGF0ZTphbnkpOiBFbGVtZW50W10ge1xuICAgIC8vIFRoZSBxdWVzdGlvbnMgdG8gc2hvdyBhdCBhbnkgdGltZSBhcmUgdGhvc2Ugd2hvc2UgcHJlY29uZGl0aW9uc1xuICAgIC8vIGFyZSBmdWxmaWxsZWRcbiAgICByZXR1cm4gZWxlbWVudHMuZmlsdGVyKGVsID0+IGV2YWxFbGVtZW50KGVsLCBzdGF0ZSkpO1xufVxuIFxuIiwiaW1wb3J0IHsgY3JlYXRlQWN0aW9uLCBoYW5kbGVBY3Rpb25zIH0gZnJvbSAncmVkdXgtYWN0aW9ucyc7XG5cbmV4cG9ydCBjb25zdCBnb1ByZXZpb3VzICA9IGNyZWF0ZUFjdGlvbihcIlBST01TX1BSRVZJT1VTXCIpO1xuZXhwb3J0IGNvbnN0IGdvTmV4dCA9IGNyZWF0ZUFjdGlvbihcIlBST01TX05FWFRcIik7XG5leHBvcnQgY29uc3Qgc3VibWl0QW5zd2VycyA9IGNyZWF0ZUFjdGlvbihcIlBST01TX1NVQk1JVFwiKTtcbmV4cG9ydCBjb25zdCBlbnRlckRhdGEgPSBjcmVhdGVBY3Rpb24oXCJQUk9NU19FTlRFUl9EQVRBXCIpO1xuXG5pbXBvcnQgeyBldmFsRWxlbWVudHMgfSBmcm9tICcuLi9sb2dpYyc7XG5pbXBvcnQgYXhpb3MgZnJvbSAnYXhpb3MnO1xuXG5heGlvcy5kZWZhdWx0cy54c3JmSGVhZGVyTmFtZSA9IFwiWC1DU1JGVE9LRU5cIjtcbmF4aW9zLmRlZmF1bHRzLnhzcmZDb29raWVOYW1lID0gXCJjc3JmdG9rZW5cIjtcblxuZnVuY3Rpb24gc3VibWl0U3VydmV5KGFuc3dlcnM6IHtbaW5kZXg6c3RyaW5nXTogc3RyaW5nfSkge1xuICAgIGxldCBwYXRpZW50VG9rZW46c3RyaW5nID0gd2luZG93LnByb21zX2NvbmZpZy5wYXRpZW50X3Rva2VuO1xuICAgIGxldCByZWdpc3RyeUNvZGU6IHN0cmluZyA9IHdpbmRvdy5wcm9tc19jb25maWcucmVnaXN0cnlfY29kZTtcbiAgICBsZXQgc3VydmV5TmFtZTogc3RyaW5nID0gd2luZG93LnByb21zX2NvbmZpZy5zdXJ2ZXlfbmFtZTtcbiAgICBsZXQgc3VydmV5RW5kcG9pbnQ6c3RyaW5nID0gd2luZG93LnByb21zX2NvbmZpZy5zdXJ2ZXlfZW5kcG9pbnQ7XG4gICAgbGV0IGRhdGEgPSB7cGF0aWVudF90b2tlbjogcGF0aWVudFRva2VuLFxuXHRcdHJlZ2lzdHJ5X2NvZGU6IHJlZ2lzdHJ5Q29kZSxcblx0ICAgICAgICBzdXJ2ZXlfbmFtZTogc3VydmV5TmFtZSxcblx0ICAgICAgICBhbnN3ZXJzOiBhbnN3ZXJzfTtcbiAgICBheGlvcy5wb3N0KHN1cnZleUVuZHBvaW50LCBkYXRhKVxuXHQudGhlbihyZXMgPT4gd2luZG93LmxvY2F0aW9uLnJlcGxhY2Uod2luZG93LnByb21zX2NvbmZpZy5jb21wbGV0ZWRfcGFnZSkpXG5cdC5jYXRjaChlcnIgPT4gYWxlcnQoZXJyLnRvU3RyaW5nKCkpKTtcbn1cblxuXG5cbmNvbnN0IGluaXRpYWxTdGF0ZSA9IHtcbiAgICBzdGFnZTogMCxcbiAgICBhbnN3ZXJzOiB7fSxcbiAgICBxdWVzdGlvbnM6IGV2YWxFbGVtZW50cyh3aW5kb3cucHJvbXNfY29uZmlnLnF1ZXN0aW9ucywge2Fuc3dlcnM6IHt9fSksXG4gICAgdGl0bGU6ICcnLFxufVxuXG5mdW5jdGlvbiBpc0NvbmQoc3RhdGUpIHtcbiAgICBjb25zdCBzdGFnZSA9IHN0YXRlLnN0YWdlO1xuICAgIHJldHVybiBzdGF0ZS5xdWVzdGlvbnNbc3RhZ2VdLnRhZyA9PSAnY29uZCc7XG59XG5cblxuZnVuY3Rpb24gdXBkYXRlQW5zd2VycyhhY3Rpb246IGFueSwgc3RhdGU6IGFueSkgOiBhbnkge1xuICAgIC8vIGlmIGRhdGEgZW50ZXJlZCAsIHVwZGF0ZSB0aGUgYW5zd2VycyBvYmplY3RcbiAgICBsZXQgY2RlQ29kZSA9IGFjdGlvbi5wYXlsb2FkLmNkZTtcbiAgICBsZXQgbmV3VmFsdWUgPSBhY3Rpb24ucGF5bG9hZC52YWx1ZTtcbiAgICBsZXQgb2xkQW5zd2VycyA9IHN0YXRlLmFuc3dlcnM7XG4gICAgdmFyIG5ld0Fuc3dlcnMgPSB7Li4ub2xkQW5zd2Vyc307XG4gICAgbmV3QW5zd2Vyc1tjZGVDb2RlXSA9IG5ld1ZhbHVlO1xuICAgIHJldHVybiBuZXdBbnN3ZXJzO1xufVxuXG5leHBvcnQgY29uc3QgcHJvbXNQYWdlUmVkdWNlciA9IGhhbmRsZUFjdGlvbnMoe1xuICAgIFtnb1ByZXZpb3VzIGFzIGFueV06XG4gICAgKHN0YXRlLCBhY3Rpb246IGFueSkgPT4gKHtcblx0Li4uc3RhdGUsXG5cdHN0YWdlOiBzdGF0ZS5zdGFnZSAtIDEsXG4gICAgfSksXG4gICAgW2dvTmV4dCBhcyBhbnldOlxuICAgIChzdGF0ZSwgYWN0aW9uOiBhbnkpID0+ICh7XG5cdC4uLnN0YXRlLFxuXHRzdGFnZTogc3RhdGUuc3RhZ2UgKyAxLFxuICAgIH0pLFxuICAgIFtzdWJtaXRBbnN3ZXJzIGFzIGFueV06XG4gICAgKHN0YXRlLCBhY3Rpb246IGFueSkgPT4ge1xuXHRjb25zb2xlLmxvZyhcInN1Ym1pdHRpbmcgYW5zd2Vyc1wiKTtcblx0c3VibWl0U3VydmV5KHN0YXRlLmFuc3dlcnMpO1xuXHRyZXR1cm4gc3RhdGU7XG4gICAgfSxcbiAgICBbZW50ZXJEYXRhIGFzIGFueV06XG4gICAgKHN0YXRlLCBhY3Rpb24pID0+IHtcblx0Y29uc29sZS5sb2coXCJlbnRlckRhdGEgYWN0aW9uIHJlY2VpdmVkXCIpO1xuXHRjb25zb2xlLmxvZyhcImFjdGlvbiA9IFwiICsgYWN0aW9uLnRvU3RyaW5nKCkpO1xuXHRjb25zb2xlLmxvZyhcImFuc3dlcnMgYmVmb3JlIHVwZGF0ZSA9IFwiICsgc3RhdGUuYW5zd2Vycy50b1N0cmluZygpKTtcblx0bGV0IHVwZGF0ZWRBbnN3ZXJzID0gdXBkYXRlQW5zd2VycyhhY3Rpb24sIHN0YXRlKVxuXHRjb25zb2xlLmxvZyhcInVwZGF0ZWQgYW5zd2VycyA9IFwiICsgdXBkYXRlZEFuc3dlcnMudG9TdHJpbmcoKSk7XG5cdGxldCBuZXdTdGF0ZSA9IHtcblx0ICAgIC4uLnN0YXRlLFxuXHQgICAgYW5zd2VyczogdXBkYXRlQW5zd2VycyhhY3Rpb24sIHN0YXRlKSxcblx0ICAgIHF1ZXN0aW9uczogZXZhbEVsZW1lbnRzKHdpbmRvdy5wcm9tc19jb25maWcucXVlc3Rpb25zLHthbnN3ZXJzOiB1cGRhdGVkQW5zd2Vyc30pLFxuXHR9O1xuXHRjb25zb2xlLmxvZyhcIm5ld1N0YXRlID0gXCIgKyBuZXdTdGF0ZS50b1N0cmluZygpKTtcblx0cmV0dXJuIG5ld1N0YXRlO1xuICAgIH0sXHRcbn0sIGluaXRpYWxTdGF0ZSk7XG4iXSwic291cmNlUm9vdCI6IiJ9