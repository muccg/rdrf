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
var react_device_detect_1 = __webpack_require__(/*! react-device-detect */ "./node_modules/react-device-detect/dist/index.js");
var go_1 = __webpack_require__(/*! react-icons/go */ "./node_modules/react-icons/go/index.js");
var reactstrap_1 = __webpack_require__(/*! reactstrap */ "./node_modules/reactstrap/dist/reactstrap.es.js");
var reactstrap_2 = __webpack_require__(/*! reactstrap */ "./node_modules/reactstrap/dist/reactstrap.es.js");
var App = /** @class */ (function (_super) {
    __extends(App, _super);
    function App(props) {
        var _this = _super.call(this, props) || this;
        _this.moveNext = _this.moveNext.bind(_this);
        _this.movePrevious = _this.movePrevious.bind(_this);
        return _this;
    }
    App.prototype.atEnd = function () {
        var lastIndex = this.props.questions.length - 1;
        return this.props.stage === lastIndex;
    };
    App.prototype.atBeginning = function () {
        return this.props.stage === 0;
    };
    App.prototype.getProgress = function () {
        var numQuestions = this.props.questions.length;
        var consentQuestionCode = this.props.questions[numQuestions - 1].cde;
        // last question is considered as consent
        var allAnswers = Object.keys(this.props.answers).filter(function (val) {
            return val !== consentQuestionCode;
        });
        var numAnswers = allAnswers.length;
        numQuestions = numQuestions - 1; // consent not considered
        return Math.floor(100.00 * (numAnswers / numQuestions));
    };
    App.prototype.movePrevious = function () {
        if (!this.atBeginning()) {
            this.props.goPrevious();
        }
    };
    App.prototype.moveNext = function () {
        if (!this.atEnd()) {
            this.props.goNext();
        }
    };
    App.prototype.render = function () {
        var nextButton;
        var backButton;
        var submitButton;
        var progressBar;
        var source;
        var style = { height: "100%" };
        if (this.atEnd()) {
            !react_device_detect_1.isMobile ?
                nextButton = (React.createElement(reactstrap_2.Col, { sm: { size: 4, order: 2, offset: 1 } },
                    React.createElement(reactstrap_2.Button, { onClick: this.props.submitAnswers, color: "success", size: "sm" }, "Submit Answers")))
                :
                    submitButton = (React.createElement("div", { className: "text-center" },
                        React.createElement(reactstrap_2.Button, { onClick: this.props.submitAnswers, color: "success", size: "sm" }, "Submit Answers")));
        }
        else {
            nextButton = !react_device_detect_1.isMobile ?
                (React.createElement(reactstrap_2.Col, { sm: { size: 1 } },
                    React.createElement(reactstrap_2.Button, { onClick: this.moveNext, size: "sm", color: "info" }, "Next"))) :
                (React.createElement("i", { onClick: this.moveNext },
                    " ",
                    React.createElement(go_1.GoChevronRight, { style: { fontSize: '56px' } }),
                    " "));
        }
        if (this.atBeginning()) {
            backButton = !react_device_detect_1.isMobile ?
                (React.createElement(reactstrap_2.Col, { sm: { size: 1 } },
                    React.createElement(reactstrap_2.Button, { onClick: this.movePrevious, color: "info", size: "sm", disabled: true }, "Previous"))) : (React.createElement("i", { onClick: this.movePrevious },
                " ",
                React.createElement(go_1.GoChevronLeft, { style: { fontSize: '56px' } }),
                " "));
        }
        else {
            backButton = !react_device_detect_1.isMobile ?
                (React.createElement(reactstrap_2.Col, { sm: { size: 1 } },
                    React.createElement(reactstrap_2.Button, { onClick: this.movePrevious, color: "info", size: "sm" }, "Previous"))) : (React.createElement("i", { onClick: this.movePrevious },
                " ",
                React.createElement(go_1.GoChevronLeft, { style: { fontSize: '56px' } }),
                " "));
        }
        if (!this.atEnd()) {
            progressBar = (React.createElement(reactstrap_2.Col, null,
                React.createElement(reactstrap_1.Progress, { color: "info", value: this.getProgress() },
                    this.getProgress(),
                    "%")));
        }
        if (this.props.questions[this.props.stage].source) {
            source = (React.createElement("div", { className: "text-center text-muted", style: { fontSize: '12px' } },
                " Source:",
                this.props.questions[this.props.stage].source));
        }
        return (React.createElement("div", { className: "App", style: style },
            React.createElement(reactstrap_2.Container, { style: style },
                React.createElement("div", { className: "mb-4" },
                    React.createElement(reactstrap_2.Row, null,
                        React.createElement(reactstrap_2.Col, null,
                            React.createElement(instruction_1.default, { stage: this.props.stage }))),
                    React.createElement(reactstrap_2.Row, null,
                        React.createElement(reactstrap_2.Col, null,
                            React.createElement(question_1.default, { title: this.props.title, stage: this.props.stage, questions: this.props.questions })))),
                React.createElement("div", { className: "mb-4" },
                    React.createElement(reactstrap_2.Row, null,
                        backButton,
                        progressBar,
                        nextButton)),
                submitButton),
            React.createElement("footer", { className: "footer", style: { height: 'auto' } },
                source,
                React.createElement("div", { className: "text-center text-muted", style: { fontSize: '12px' } }, this.props.questions[this.props.stage].copyright_text))));
    };
    return App;
}(React.Component));
function mapStateToProps(state) {
    return {
        stage: state.stage,
        title: state.title,
        answers: state.answers,
        questions: state.questions
    };
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
/* WEBPACK VAR INJECTION */(function(global) {
Object.defineProperty(exports, "__esModule", { value: true });
__webpack_require__(/*! bootstrap/dist/css/bootstrap.min.css */ "./node_modules/bootstrap/dist/css/bootstrap.min.css");
var React = __webpack_require__(/*! react */ "./node_modules/react/index.js");
var ReactDOM = __webpack_require__(/*! react-dom */ "./node_modules/react-dom/index.js");
var react_redux_1 = __webpack_require__(/*! react-redux */ "./node_modules/react-redux/es/index.js");
var redux_1 = __webpack_require__(/*! redux */ "./node_modules/redux/es/redux.js");
var redux_thunk_1 = __webpack_require__(/*! redux-thunk */ "./node_modules/redux-thunk/es/index.js");
var app_1 = __webpack_require__(/*! ./app */ "./src/app/index.tsx");
var reducers_1 = __webpack_require__(/*! ./pages/proms_page/reducers */ "./src/pages/proms_page/reducers/index.ts");
var devtoolsExtension = '__REDUX_DEVTOOLS_EXTENSION_COMPOSE__';
var composeEnhancers = window[devtoolsExtension] || redux_1.compose;
exports.store = redux_1.createStore(reducers_1.promsPageReducer, composeEnhancers(redux_1.applyMiddleware(redux_thunk_1.default)));
var unsubscribe = exports.store.subscribe(function () {
    return global.console.log(exports.store.getState());
});
ReactDOM.render(React.createElement(react_redux_1.Provider, { store: exports.store },
    React.createElement(app_1.default, null)), document.getElementById('app'));

/* WEBPACK VAR INJECTION */}.call(this, __webpack_require__(/*! ./../node_modules/webpack/buildin/global.js */ "./node_modules/webpack/buildin/global.js")))

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
var __assign = (this && this.__assign) || Object.assign || function(t) {
    for (var s, i = 1, n = arguments.length; i < n; i++) {
        s = arguments[i];
        for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
            t[p] = s[p];
    }
    return t;
};
var __rest = (this && this.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) if (e.indexOf(p[i]) < 0)
            t[p[i]] = s[p[i]];
    return t;
};
Object.defineProperty(exports, "__esModule", { value: true });
var _ = __webpack_require__(/*! lodash */ "./node_modules/lodash/lodash.js");
var rc_slider_1 = __webpack_require__(/*! rc-slider */ "./node_modules/rc-slider/es/index.js");
__webpack_require__(/*! rc-slider/assets/index.css */ "./node_modules/rc-slider/assets/index.css");
var rc_tooltip_1 = __webpack_require__(/*! rc-tooltip */ "./node_modules/rc-tooltip/es/index.js");
var React = __webpack_require__(/*! react */ "./node_modules/react/index.js");
var react_redux_1 = __webpack_require__(/*! react-redux */ "./node_modules/react-redux/es/index.js");
var reactstrap_1 = __webpack_require__(/*! reactstrap */ "./node_modules/reactstrap/dist/reactstrap.es.js");
var actions = __webpack_require__(/*! ../reducers */ "./src/pages/proms_page/reducers/index.ts");
var Question = /** @class */ (function (_super) {
    __extends(Question, _super);
    function Question(props) {
        var _this = _super.call(this, props) || this;
        _this.onSliderChange = function (value) {
            var code = _this.props.questions[_this.props.stage].cde;
            _this.props.enterData(code, value);
        };
        _this.getMarks = function (question) {
            var minValue = question.spec.min;
            var maxValue = question.spec.max;
            var marks = (_a = {},
                _a[minValue] = React.createElement("strong", null, minValue),
                _a[10] = '10',
                _a[20] = '20',
                _a[30] = '30',
                _a[40] = '40',
                _a[50] = '50',
                _a[60] = '60',
                _a[70] = '70',
                _a[80] = '80',
                _a[90] = '90',
                _a[maxValue] = {
                    style: {
                        color: 'red',
                    },
                    label: React.createElement("strong", null, maxValue),
                },
                _a);
            return marks;
            var _a;
        };
        _this.getSliderHandle = function () {
            var Handle = rc_slider_1.default.Handle;
            var handle = function (props) {
                var value = props.value, dragging = props.dragging, index = props.index, restProps = __rest(props, ["value", "dragging", "index"]);
                return (React.createElement(rc_tooltip_1.default, { prefixCls: "rc-slider-tooltip", overlay: value, visible: dragging, placement: "top", key: index },
                    React.createElement(Handle, __assign({ value: value }, restProps))));
            };
            return handle;
        };
        _this.onSliderChange = _this.onSliderChange.bind(_this);
        _this.handleConsent = _this.handleConsent.bind(_this);
        _this.handleChange = _this.handleChange.bind(_this);
        _this.handleMultiChange = _this.handleMultiChange.bind(_this);
        return _this;
    }
    Question.prototype.handleChange = function (event) {
        var cdeValue = event.target.value;
        var cdeCode = event.target.name;
        this.props.enterData(cdeCode, cdeValue);
    };
    Question.prototype.handleMultiChange = function (event) {
        var cdeCode = event.target.name;
        var values;
        var options;
        options = event.target.options;
        values = [];
        _.each(event.target.options, function (option) {
            if (option.selected) {
                values.push(option.value);
            }
        });
        this.props.enterData(cdeCode, values);
    };
    Question.prototype.handleConsent = function (event) {
        var isConsentChecked = event.target.checked;
        var cdeCode = event.target.name;
        this.props.enterData(cdeCode, isConsentChecked);
    };
    Question.prototype.renderMultiSelect = function (question) {
        return (React.createElement(reactstrap_1.Form, null,
            React.createElement(reactstrap_1.FormGroup, { tag: "fieldset" },
                React.createElement("h6", null,
                    React.createElement("i", null, question.survey_question_instruction)),
                React.createElement("h4", null, question.title),
                React.createElement("i", null, question.instructions)),
            React.createElement(reactstrap_1.FormGroup, null,
                React.createElement(reactstrap_1.Col, { sm: "12", md: { size: 6, offset: 3 } },
                    React.createElement(reactstrap_1.Input, { type: "select", name: question.cde, onChange: this.handleMultiChange, multiple: true }, _.map(question.spec.options, function (option, index) { return (React.createElement("option", { key: option.code, value: option.code }, option.text)); }))))));
    };
    Question.prototype.render = function () {
        var _this = this;
        var question = this.props.questions[this.props.stage];
        var defaultValue = 0;
        if (question.spec.tag === 'integer') {
            if (this.props.answers[question.cde] !== undefined) {
                defaultValue = this.props.answers[question.cde];
            }
            else {
                this.onSliderChange(defaultValue);
            }
        }
        var boxStyle = { width: "100px", height: "100px", backgroundColor: "black" };
        var pStyle = { color: "white", align: "center" };
        var style = { width: "50%", height: "50vh", margin: "0 auto", leftPadding: "100px" };
        var isLast = (this.props.questions.length - 1) === this.props.stage;
        var isConsent = question.cde === "PROMSConsent";
        var consentText = React.createElement("div", null,
            "By ticking this box you:",
            React.createElement("ul", null,
                React.createElement("li", null, "Give consent for the information you provide to be used for the CIC Cancer project; and "),
                React.createElement("li", null, "Will receive a reminder when the next survey is due.")));
        var isMultiSelect = question.spec.tag === 'range' && question.spec.allow_multiple;
        if (isMultiSelect) {
            return this.renderMultiSelect(question);
        }
        return (React.createElement(reactstrap_1.Form, null,
            React.createElement(reactstrap_1.FormGroup, { tag: "fieldset" },
                React.createElement("h6", null,
                    React.createElement("i", null, this.props.questions[this.props.stage].survey_question_instruction)),
                React.createElement("h4", null, this.props.questions[this.props.stage].title),
                React.createElement("i", null, this.props.questions[this.props.stage].instructions)),
            (question.spec.tag === 'integer' ?
                React.createElement("div", { className: 'row' },
                    React.createElement("div", { className: "col" },
                        React.createElement("div", { className: "float-right", style: boxStyle },
                            React.createElement("p", { className: "text-center", style: pStyle },
                                "YOUR HEALTH RATE TODAY ",
                                React.createElement("b", null, defaultValue)))),
                    React.createElement("div", { className: "col", style: style },
                        React.createElement(rc_slider_1.default, { vertical: true, min: question.spec.min, max: question.spec.max, defaultValue: defaultValue, marks: this.getMarks(question), handle: this.getSliderHandle(), onChange: this.onSliderChange })))
                :
                    isConsent ?
                        React.createElement(reactstrap_1.FormGroup, { check: true },
                            React.createElement(reactstrap_1.Label, { check: true },
                                React.createElement(reactstrap_1.Input, { type: "checkbox", name: this.props.questions[this.props.stage].cde, onChange: this.handleConsent, checked: this.props.answers[question.cde] }),
                                consentText))
                        :
                            _.map(question.spec.tag === 'range' ? question.spec.options : [], function (option, index) { return (React.createElement(reactstrap_1.FormGroup, { check: true },
                                React.createElement(reactstrap_1.Col, { sm: "12", md: { size: 6, offset: 3 } },
                                    React.createElement(reactstrap_1.Label, { check: true },
                                        React.createElement(reactstrap_1.Input, { type: "radio", name: _this.props.questions[_this.props.stage].cde, value: option.code, onChange: _this.handleChange, checked: option.code === _this.props.answers[question.cde] }),
                                        option.text)))); }))));
    };
    return Question;
}(React.Component));
function mapStateToProps(state) {
    return {
        questions: state.questions,
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
                return answer === cond.value;
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
var axios_1 = __webpack_require__(/*! axios */ "./node_modules/axios/index.js");
var redux_actions_1 = __webpack_require__(/*! redux-actions */ "./node_modules/redux-actions/es/index.js");
exports.goPrevious = redux_actions_1.createAction("PROMS_PREVIOUS");
exports.goNext = redux_actions_1.createAction("PROMS_NEXT");
exports.submitAnswers = redux_actions_1.createAction("PROMS_SUBMIT");
exports.enterData = redux_actions_1.createAction("PROMS_ENTER_DATA");
var logic_1 = __webpack_require__(/*! ../logic */ "./src/pages/proms_page/logic.ts");
axios_1.default.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios_1.default.defaults.xsrfCookieName = "csrftoken";
function submitSurvey(answers) {
    var patient_token = window.proms_config.patient_token;
    var registry_code = window.proms_config.registry_code;
    var survey_name = window.proms_config.survey_name;
    var surveyEndpoint = window.proms_config.survey_endpoint;
    var data = {
        patient_token: patient_token,
        registry_code: registry_code,
        survey_name: survey_name,
        answers: answers
    };
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
    return state.questions[stage].tag === 'cond';
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
function clearAnswerOnSwipeBack(state) {
    // clear the answer when move to previous question
    var stage = state.stage;
    var questionCode = state.questions[stage].cde;
    var oldAnswers = state.answers;
    var newAnswers = __assign({}, oldAnswers);
    delete newAnswers[questionCode];
    return newAnswers;
}
function updateConsent(state) {
    var questionCount = state.questions.length;
    var allAnswers = state.answers;
    var questionCode = state.questions[questionCount - 1].cde;
    if (!allAnswers.hasOwnProperty(questionCode)) {
        var oldAnswers = state.answers;
        var newAnswers = __assign({}, oldAnswers);
        newAnswers[questionCode] = false;
        return newAnswers;
    }
    return allAnswers;
}
exports.promsPageReducer = redux_actions_1.handleActions((_a = {},
    _a[exports.goPrevious] = function (state, action) { return (__assign({}, state, { answers: clearAnswerOnSwipeBack(state), stage: state.stage - 1 })); },
    _a[exports.goNext] = function (state, action) { return (__assign({}, state, { stage: state.stage + 1 })); },
    _a[exports.submitAnswers] = function (state, action) {
        var newState = __assign({}, state, { answers: updateConsent(state) });
        submitSurvey(newState.answers);
        return newState;
    },
    _a[exports.enterData] = function (state, action) {
        var updatedAnswers = updateAnswers(action, state);
        var newState = __assign({}, state, { answers: updateAnswers(action, state), questions: logic_1.evalElements(window.proms_config.questions, { answers: updatedAnswers }) });
        return newState;
    },
    _a), initialState);
var _a;


/***/ })

},[["./src/init.tsx","runtime","vendors"]]]);
//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly9yZHJmdHMvLi9zcmMvYXBwL2luZGV4LnRzeCIsIndlYnBhY2s6Ly9yZHJmdHMvLi9zcmMvaW5pdC50c3giLCJ3ZWJwYWNrOi8vcmRyZnRzLy4vc3JjL3BhZ2VzL3Byb21zX3BhZ2UvY29tcG9uZW50cy9pbnN0cnVjdGlvbi50c3giLCJ3ZWJwYWNrOi8vcmRyZnRzLy4vc3JjL3BhZ2VzL3Byb21zX3BhZ2UvY29tcG9uZW50cy9xdWVzdGlvbi50c3giLCJ3ZWJwYWNrOi8vcmRyZnRzLy4vc3JjL3BhZ2VzL3Byb21zX3BhZ2UvbG9naWMudHMiLCJ3ZWJwYWNrOi8vcmRyZnRzLy4vc3JjL3BhZ2VzL3Byb21zX3BhZ2UvcmVkdWNlcnMvaW5kZXgudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFBQSw4RUFBK0I7QUFDL0IscUdBQXNDO0FBQ3RDLG1GQUEyQztBQUUzQywrSUFBcUU7QUFDckUsc0lBQStEO0FBQy9ELHFIQUFpRjtBQUVqRiwrSEFBK0M7QUFDL0MsK0ZBQStEO0FBQy9ELDRHQUFzQztBQUN0Qyw0R0FBeUQ7QUFlekQ7SUFBa0IsdUJBQXFDO0lBQ25ELGFBQVksS0FBSztRQUFqQixZQUNJLGtCQUFNLEtBQUssQ0FBQyxTQUdmO1FBRkcsS0FBSSxDQUFDLFFBQVEsR0FBRyxLQUFJLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxLQUFJLENBQUMsQ0FBQztRQUN6QyxLQUFJLENBQUMsWUFBWSxHQUFHLEtBQUksQ0FBQyxZQUFZLENBQUMsSUFBSSxDQUFDLEtBQUksQ0FBQyxDQUFDOztJQUNyRCxDQUFDO0lBRU0sbUJBQUssR0FBWjtRQUNJLElBQU0sU0FBUyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsU0FBUyxDQUFDLE1BQU0sR0FBRyxDQUFDLENBQUM7UUFDbEQsT0FBTyxJQUFJLENBQUMsS0FBSyxDQUFDLEtBQUssS0FBSyxTQUFTLENBQUM7SUFDMUMsQ0FBQztJQUVNLHlCQUFXLEdB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SUFDcEIsQ0FBQztTQUNOLFlBQVksQ0FBQyxDQUFDIiwiZmlsZSI6Im1haW4tYnVuZGxlLmpzIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0ICogYXMgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgY29ubmVjdCB9IGZyb20gJ3JlYWN0LXJlZHV4JztcbmltcG9ydCB7IGJpbmRBY3Rpb25DcmVhdG9ycyB9IGZyb20gJ3JlZHV4JztcblxuaW1wb3J0IEluc3RydWN0aW9uIGZyb20gJy4uL3BhZ2VzL3Byb21zX3BhZ2UvY29tcG9uZW50cy9pbnN0cnVjdGlvbic7XG5pbXBvcnQgUXVlc3Rpb24gZnJvbSAnLi4vcGFnZXMvcHJvbXNfcGFnZS9jb21wb25lbnRzL3F1ZXN0aW9uJztcbmltcG9ydCB7IGdvTmV4dCwgZ29QcmV2aW91cywgc3VibWl0QW5zd2VycyB9IGZyb20gJy4uL3BhZ2VzL3Byb21zX3BhZ2UvcmVkdWNlcnMnO1xuXG5pbXBvcnQgeyBpc01vYmlsZSB9IGZyb20gJ3JlYWN0LWRldmljZS1kZXRlY3QnO1xuaW1wb3J0IHsgR29DaGV2cm9uTGVmdCwgR29DaGV2cm9uUmlnaHQgfSBmcm9tICdyZWFjdC1pY29ucy9nbyc7XG5pbXBvcnQgeyBQcm9ncmVzcyB9IGZyb20gJ3JlYWN0c3RyYXAnO1xuaW1wb3J0IHsgQnV0dG9uLCBDb2wsIENvbnRhaW5lciwgUm93IH0gZnJvbSAncmVhY3RzdHJhcCc7XG5pbXBvcnQgeyBFbGVtZW50TGlzdCB9IGZyb20gJy4uL3BhZ2VzL3Byb21zX3BhZ2UvbG9naWMnO1xuXG5cbmludGVyZmFjZSBBcHBJbnRlcmZhY2Uge1xuICAgIHRpdGxlOiBzdHJpbmcsXG4gICAgc3RhZ2U6IG51bWJlcixcbiAgICBhbnN3ZXJzOiBhbnksXG4gICAgcXVlc3Rpb25zOiBFbGVtZW50TGlzdCxcbiAgICBnb05leHQ6IGFueSxcbiAgICBnb1ByZXZpb3VzOiBhbnksXG4gICAgc3VibWl0QW5zd2VyczogYW55LFxufVxuXG5cbmNsYXNzIEFwcCBleHRlbmRzIFJlYWN0LkNvbXBvbmVudDxBcHBJbnRlcmZhY2UsIG9iamVjdD4ge1xuICAgIGNvbnN0cnVjdG9yKHByb3BzKSB7XG4gICAgICAgIHN1cGVyKHByb3BzKTtcbiAgICAgICAgdGhpcy5tb3ZlTmV4dCA9IHRoaXMubW92ZU5leHQuYmluZCh0aGlzKTtcbiAgICAgICAgdGhpcy5tb3ZlUHJldmlvdXMgPSB0aGlzLm1vdmVQcmV2aW91cy5iaW5kKHRoaXMpO1xuICAgIH1cblxuICAgIHB1YmxpYyBhdEVuZCgpIHtcbiAgICAgICAgY29uc3QgbGFzdEluZGV4ID0gdGhpcy5wcm9wcy5xdWVzdGlvbnMubGVuZ3RoIC0gMTtcbiAgICAgICAgcmV0dXJuIHRoaXMucHJvcHMuc3RhZ2UgPT09IGxhc3RJbmRleDtcbiAgICB9XG5cbiAgICBwdWJsaWMgYXRCZWdpbm5pbmcoKSB7XG4gICAgICAgIHJldHVybiB0aGlzLnByb3BzLnN0YWdlID09PSAwO1xuICAgIH1cblxuXG4gICAgcHVibGljIGdldFByb2dyZXNzKCk6IG51bWJlciB7XG4gICAgICAgIGxldCBudW1RdWVzdGlvbnM6IG51bWJlciA9IHRoaXMucHJvcHMucXVlc3Rpb25zLmxlbmd0aDtcbiAgICAgICAgY29uc3QgY29uc2VudFF1ZXN0aW9uQ29kZSA9IHRoaXMucHJvcHMucXVlc3Rpb25zW251bVF1ZXN0aW9ucyAtIDFdLmNkZTtcbiAgICAgICAgLy8gbGFzdCBxdWVzdGlvbiBpcyBjb25zaWRlcmVkIGFzIGNvbnNlbnRcbiAgICAgICAgY29uc3QgYWxsQW5zd2VycyA9IE9iamVjdC5rZXlzKHRoaXMucHJvcHMuYW5zd2VycykuZmlsdGVyKHZhbCA9PiB7XG4gICAgICAgICAgICByZXR1cm4gdmFsICE9PSBjb25zZW50UXVlc3Rpb25Db2RlO1xuICAgICAgICB9KTtcbiAgICAgICAgY29uc3QgbnVtQW5zd2VyczogbnVtYmVyID0gYWxsQW5zd2Vycy5sZW5ndGg7XG4gICAgICAgIG51bVF1ZXN0aW9ucyA9IG51bVF1ZXN0aW9ucyAtIDE7IC8vIGNvbnNlbnQgbm90IGNvbnNpZGVyZWRcbiAgICAgICAgcmV0dXJuIE1hdGguZmxvb3IoMTAwLjAwICogKG51bUFuc3dlcnMgLyBudW1RdWVzdGlvbnMpKTtcbiAgICB9XG5cbiAgICBwdWJsaWMgbW92ZVByZXZpb3VzKCkge1xuICAgICAgICBpZiAoIXRoaXMuYXRCZWdpbm5pbmcoKSkge1xuICAgICAgICAgICAgdGhpcy5wcm9wcy5nb1ByZXZpb3VzKCk7XG4gICAgICAgIH1cbiAgICB9XG5cbiAgICBwdWJsaWMgbW92ZU5leHQoKSB7XG4gICAgICAgIGlmICghdGhpcy5hdEVuZCgpKSB7XG4gICAgICAgICAgICB0aGlzLnByb3BzLmdvTmV4dCgpO1xuICAgICAgICB9XG4gICAgfVxuXG4gICAgcHVibGljIHJlbmRlcigpIHtcbiAgICAgICAgbGV0IG5leHRCdXR0b247XG4gICAgICAgIGxldCBiYWNrQnV0dG9uO1xuICAgICAgICBsZXQgc3VibWl0QnV0dG9uO1xuICAgICAgICBsZXQgcHJvZ3Jlc3NCYXI7XG4gICAgICAgIGxldCBzb3VyY2U7XG4gICAgICAgIGNvbnN0IHN0eWxlID0geyBoZWlnaHQ6XCIxMDAlXCIgfTtcblxuICAgICAgICBpZiAodGhpcy5hdEVuZCgpKSB7XG4gICAgICAgICAgICAhaXNNb2JpbGUgPyBcbiAgICAgICAgICAgIG5leHRCdXR0b24gPSAoPENvbCBzbT17eyBzaXplOiA0LCBvcmRlcjogMiwgb2Zmc2V0OiAxIH19PlxuICAgICAgICAgICAgICAgIDxCdXR0b24gb25DbGljaz17dGhpcy5wcm9wcy5zdWJtaXRBbnN3ZXJzfSBjb2xvcj1cInN1Y2Nlc3NcIiBzaXplPVwic21cIj5TdWJtaXQgQW5zd2VyczwvQnV0dG9uPlxuICAgICAgICAgICAgPC9Db2w+KVxuICAgICAgICAgICAgOlxuICAgICAgICAgICAgc3VibWl0QnV0dG9uID0gKFxuICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwidGV4dC1jZW50ZXJcIj5cbiAgICAgICAgICAgICAgICAgICAgPEJ1dHRvbiBvbkNsaWNrPXt0aGlzLnByb3BzLnN1Ym1pdEFuc3dlcnN9IGNvbG9yPVwic3VjY2Vzc1wiIHNpemU9XCJzbVwiPlN1Ym1pdCBBbnN3ZXJzPC9CdXR0b24+XG4gICAgICAgICAgICAgICAgPC9kaXY+XG4gICAgICAgICAgICApXG4gICAgICAgIH1cbiAgICAgICAgZWxzZSB7XG4gICAgICAgICAgICBuZXh0QnV0dG9uID0gIWlzTW9iaWxlID8gXG4gICAgICAgICAgICAgICg8Q29sIHNtPXt7IHNpemU6IDEgfX0+XG4gICAgICAgICAgICAgICAgPEJ1dHRvbiBvbkNsaWNrPXt0aGlzLm1vdmVOZXh0fSBzaXplPVwic21cIiBjb2xvcj1cImluZm9cIj5OZXh0PC9CdXR0b24+XG4gICAgICAgICAgICA8L0NvbD4pIDpcbiAgICAgICAgICAgICAgKDxpIG9uQ2xpY2s9e3RoaXMubW92ZU5leHR9PiA8R29DaGV2cm9uUmlnaHQgc3R5bGU9e3tmb250U2l6ZTogJzU2cHgnfX0gLz4gPC9pPilcbiAgICAgICAgfVxuXG4gICAgICAgIGlmICh0aGlzLmF0QmVnaW5uaW5nKCkpIHtcbiAgICAgICAgICAgIGJhY2tCdXR0b24gPSAhaXNNb2JpbGUgPyBcbiAgICAgICAgICAgICAgKDxDb2wgc209e3sgc2l6ZTogMSB9fT5cbiAgICAgICAgICAgICAgICA8QnV0dG9uIG9uQ2xpY2s9e3RoaXMubW92ZVByZXZpb3VzfSBjb2xvcj1cImluZm9cIiBzaXplPVwic21cIiBkaXNhYmxlZD17dHJ1ZX0gPlByZXZpb3VzPC9CdXR0b24+XG4gICAgICAgICAgICAgICA8L0NvbD4pIDogKDxpIG9uQ2xpY2s9e3RoaXMubW92ZVByZXZpb3VzfT4gPEdvQ2hldnJvbkxlZnQgc3R5bGU9e3tmb250U2l6ZTogJzU2cHgnfX0gLz4gPC9pPilcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGJhY2tCdXR0b24gPSAhaXNNb2JpbGUgPyBcbiAgICAgICAgICAgICAgKDxDb2wgc209e3sgc2l6ZTogMSB9fT5cbiAgICAgICAgICAgICAgICA8QnV0dG9uIG9uQ2xpY2s9e3RoaXMubW92ZVByZXZpb3VzfSBjb2xvcj1cImluZm9cIiBzaXplPVwic21cIj5QcmV2aW91czwvQnV0dG9uPlxuICAgICAgICAgICAgICAgPC9Db2w+KSA6ICg8aSBvbkNsaWNrPXt0aGlzLm1vdmVQcmV2aW91c30+IDxHb0NoZXZyb25MZWZ0IHN0eWxlPXt7Zm9udFNpemU6ICc1NnB4J319IC8+IDwvaT4pXG4gICAgICAgIH1cblxuICAgICAgICBpZiAoIXRoaXMuYXRFbmQoKSkge1xuICAgICAgICAgICAgcHJvZ3Jlc3NCYXIgPSAoXG4gICAgICAgICAgICAgICAgPENvbD5cbiAgICAgICAgICAgICAgICAgICAgPFByb2dyZXNzIGNvbG9yPVwiaW5mb1wiIHZhbHVlPXt0aGlzLmdldFByb2dyZXNzKCl9Pnt0aGlzLmdldFByb2dyZXNzKCl9JTwvUHJvZ3Jlc3M+XG4gICAgICAgICAgICAgICAgPC9Db2w+XG4gICAgICAgICAgICApXG4gICAgICAgIH1cblxuICAgICAgICBpZiAodGhpcy5wcm9wcy5xdWVzdGlvbnNbdGhpcy5wcm9wcy5zdGFnZV0uc291cmNlKXtcbiAgICAgICAgICAgIHNvdXJjZSA9IChcbiAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cInRleHQtY2VudGVyIHRleHQtbXV0ZWRcIiBzdHlsZT17e2ZvbnRTaXplOiAnMTJweCd9fT4gU291cmNlOlxuICAgICAgICAgICAgICAgICAgICB7dGhpcy5wcm9wcy5xdWVzdGlvbnNbdGhpcy5wcm9wcy5zdGFnZV0uc291cmNlfVxuICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgKVxuICAgICAgICB9XG5cblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJBcHBcIiBzdHlsZT17c3R5bGV9PlxuICAgICAgICAgICAgICAgIDxDb250YWluZXIgc3R5bGU9e3N0eWxlfT5cbiAgICAgICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJtYi00XCI+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgPFJvdz5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPENvbD5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDxJbnN0cnVjdGlvbiBzdGFnZT17dGhpcy5wcm9wcy5zdGFnZX0gLz5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPC9Db2w+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgPC9Sb3c+XG5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICA8Um93PlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA8Q29sPlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPFF1ZXN0aW9uIHRpdGxlPXt0aGlzLnByb3BzLnRpdGxlfSBzdGFnZT17dGhpcy5wcm9wcy5zdGFnZX0gcXVlc3Rpb25zPXt0aGlzLnByb3BzLnF1ZXN0aW9uc30gLz5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPC9Db2w+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgPC9Sb3c+XG4gICAgICAgICAgICAgICAgICAgICAgICA8L2Rpdj5cblxuICAgICAgICAgICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJtYi00XCI+XG4gICAgICAgICAgICAgICAgICAgICAgICA8Um93PlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHtiYWNrQnV0dG9ufVxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHtwcm9ncmVzc0Jhcn1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB7bmV4dEJ1dHRvbn1cbiAgICAgICAgICAgICAgICAgICAgICAgIDwvUm93PlxuICAgICAgICAgICAgICAgICAgICAgICAgPC9kaXY+XG4gICAgICAgICAgICAgICAgICAgICAgICB7c3VibWl0QnV0dG9ufVxuICAgICAgICAgICAgICAgIDwvQ29udGFpbmVyPlxuICAgICAgICAgICAgICAgIDxmb290ZXIgY2xhc3NOYW1lPVwiZm9vdGVyXCIgc3R5bGU9e3toZWlnaHQ6ICdhdXRvJ319PlxuICAgICAgICAgICAgICAgICAgICB7c291cmNlfVxuICAgICAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cInRleHQtY2VudGVyIHRleHQtbXV0ZWRcIiBzdHlsZT17e2ZvbnRTaXplOiAnMTJweCd9fT5cbiAgICAgICAgICAgICAgICAgICAgICAgIHt0aGlzLnByb3BzLnF1ZXN0aW9uc1t0aGlzLnByb3BzLnN0YWdlXS5jb3B5cmlnaHRfdGV4dH1cbiAgICAgICAgICAgICAgICAgICAgPC9kaXY+XG4gICAgICAgICAgICAgICAgPC9mb290ZXI+XG4gICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgKTtcbiAgICB9XG59XG5cbmZ1bmN0aW9uIG1hcFN0YXRlVG9Qcm9wcyhzdGF0ZSkge1xuICAgIHJldHVybiB7XG4gICAgICAgIHN0YWdlOiBzdGF0ZS5zdGFnZSxcbiAgICAgICAgdGl0bGU6IHN0YXRlLnRpdGxlLFxuICAgICAgICBhbnN3ZXJzOiBzdGF0ZS5hbnN3ZXJzLFxuICAgICAgICBxdWVzdGlvbnM6IHN0YXRlLnF1ZXN0aW9uc1xuICAgIH1cbn1cblxuZnVuY3Rpb24gbWFwRGlzcGF0Y2hUb1Byb3BzKGRpc3BhdGNoKSB7XG4gICAgcmV0dXJuIGJpbmRBY3Rpb25DcmVhdG9ycyh7XG4gICAgICAgIGdvTmV4dCxcbiAgICAgICAgZ29QcmV2aW91cyxcbiAgICAgICAgc3VibWl0QW5zd2VycyxcbiAgICB9LCBkaXNwYXRjaCk7XG59XG5cbmV4cG9ydCBkZWZhdWx0IGNvbm5lY3QobWFwU3RhdGVUb1Byb3BzLCBtYXBEaXNwYXRjaFRvUHJvcHMpKEFwcCk7XG4iLCJpbXBvcnQgJ2Jvb3RzdHJhcC9kaXN0L2Nzcy9ib290c3RyYXAubWluLmNzcyc7XG5cbmltcG9ydCAqIGFzIFJlYWN0IGZyb20gJ3JlYWN0JztcbmltcG9ydCAqIGFzIFJlYWN0RE9NIGZyb20gJ3JlYWN0LWRvbSc7XG5pbXBvcnQgeyBQcm92aWRlciB9IGZyb20gJ3JlYWN0LXJlZHV4JztcbmltcG9ydCB7IGFwcGx5TWlkZGxld2FyZSwgY29tcG9zZSwgY3JlYXRlU3RvcmUgfSBmcm9tICdyZWR1eCc7XG5pbXBvcnQgdGh1bmsgZnJvbSAncmVkdXgtdGh1bmsnO1xuXG5cbmltcG9ydCBBcHAgZnJvbSAnLi9hcHAnO1xuaW1wb3J0IHsgcHJvbXNQYWdlUmVkdWNlciB9IGZyb20gJy4vcGFnZXMvcHJvbXNfcGFnZS9yZWR1Y2Vycyc7XG5cbmNvbnN0IGRldnRvb2xzRXh0ZW5zaW9uID0gJ19fUkVEVVhfREVWVE9PTFNfRVhURU5TSU9OX0NPTVBPU0VfXyc7XG5jb25zdCBjb21wb3NlRW5oYW5jZXJzID0gd2luZG93W2RldnRvb2xzRXh0ZW5zaW9uXSB8fCBjb21wb3NlO1xuXG5leHBvcnQgY29uc3Qgc3RvcmUgPSBjcmVhdGVTdG9yZShcbiAgICBwcm9tc1BhZ2VSZWR1Y2VyLFxuICAgIGNvbXBvc2VFbmhhbmNlcnMoYXBwbHlNaWRkbGV3YXJlKHRodW5rKSlcbik7XG5cblxuY29uc3QgdW5zdWJzY3JpYmUgPSBzdG9yZS5zdWJzY3JpYmUoKCkgPT5cbiAgZ2xvYmFsLmNvbnNvbGUubG9nKHN0b3JlLmdldFN0YXRlKCkpXG4pXG5cblJlYWN0RE9NLnJlbmRlcihcbiAgICA8UHJvdmlkZXIgc3RvcmU9e3N0b3JlfT5cbiAgICAgICAgICAgIDxBcHAgLz5cbiAgICA8L1Byb3ZpZGVyPixcbiAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnYXBwJykpO1xuXG5cblxuIiwiaW1wb3J0ICogYXMgUmVhY3QgZnJvbSAncmVhY3QnO1xuXG5leHBvcnQgZGVmYXVsdCBjbGFzcyBJbnN0cnVjdGlvbiBleHRlbmRzIFJlYWN0LkNvbXBvbmVudDxhbnk+IHtcbiAgICBwdWJsaWMgcmVuZGVyKCkge1xuXHRyZXR1cm4gKDxkaXYgY2xhc3NOYW1lPVwiaW5zdHJ1Y3Rpb25cIj5cblx0ICAgICAgICB7dGhpcy5wcm9wcy5pbnN0cnVjdGlvbnN9XG5cdCAgICAgICAgPC9kaXY+KTtcbiAgICB9XG59O1xuXG4iLCJpbXBvcnQgKiBhcyBfIGZyb20gJ2xvZGFzaCc7XG5pbXBvcnQgU2xpZGVyIGZyb20gJ3JjLXNsaWRlcic7XG5pbXBvcnQgJ3JjLXNsaWRlci9hc3NldHMvaW5kZXguY3NzJztcbmltcG9ydCBUb29sdGlwIGZyb20gXCJyYy10b29sdGlwXCI7XG5pbXBvcnQgKiBhcyBSZWFjdCBmcm9tICdyZWFjdCc7XG5pbXBvcnQgeyBjb25uZWN0IH0gZnJvbSAncmVhY3QtcmVkdXgnO1xuaW1wb3J0IHsgQ29sLCBGb3JtLCBGb3JtR3JvdXAsIElucHV0LCBMYWJlbCB9IGZyb20gJ3JlYWN0c3RyYXAnO1xuaW1wb3J0IHsgUXVlc3Rpb25JbnRlcmZhY2UgfSBmcm9tICcuL2ludGVyZmFjZXMnO1xuXG5pbXBvcnQgKiBhcyBhY3Rpb25zIGZyb20gJy4uL3JlZHVjZXJzJztcblxuXG5cbmNsYXNzIFF1ZXN0aW9uIGV4dGVuZHMgUmVhY3QuQ29tcG9uZW50PFF1ZXN0aW9uSW50ZXJmYWNlLCBvYmplY3Q+IHtcbiAgICBjb25zdHJ1Y3Rvcihwcm9wcykge1xuICAgICAgICBzdXBlcihwcm9wcyk7XG4gICAgICAgIHRoaXMub25TbGlkZXJDaGFuZ2UgPSB0aGlzLm9uU2xpZGVyQ2hhbmdlLmJpbmQodGhpcyk7XG4gICAgICAgIHRoaXMuaGFuZGxlQ29uc2VudCA9IHRoaXMuaGFuZGxlQ29uc2VudC5iaW5kKHRoaXMpO1xuICAgICAgICB0aGlzLmhhbmRsZUNoYW5nZSA9IHRoaXMuaGFuZGxlQ2hhbmdlLmJpbmQodGhpcyk7XG5cdHRoaXMuaGFuZGxlTXVsdGlDaGFuZ2UgPSB0aGlzLmhhbmRsZU11bHRpQ2hhbmdlLmJpbmQodGhpcyk7XG4gICAgfVxuXG4gICAgcHVibGljIGhhbmRsZUNoYW5nZShldmVudCkge1xuICAgICAgICBjb25zdCBjZGVWYWx1ZSA9IGV2ZW50LnRhcmdldC52YWx1ZTtcbiAgICAgICAgY29uc3QgY2RlQ29kZSA9IGV2ZW50LnRhcmdldC5uYW1lO1xuICAgICAgICB0aGlzLnByb3BzLmVudGVyRGF0YShjZGVDb2RlLCBjZGVWYWx1ZSk7XG4gICAgfVxuXG4gICAgcHVibGljIGhhbmRsZU11bHRpQ2hhbmdlKGV2ZW50KSB7XG5cdGNvbnN0IGNkZUNvZGUgPSBldmVudC50YXJnZXQubmFtZTtcblx0bGV0IHZhbHVlcztcblx0bGV0IG9wdGlvbnM7XG4gICAgICAgIG9wdGlvbnMgPSBldmVudC50YXJnZXQub3B0aW9ucztcbiAgICAgICAgdmFsdWVzID0gW107XG4gICAgICAgIF8uZWFjaChldmVudC50YXJnZXQub3B0aW9ucywgKG9wdGlvbjogSFRNTE9wdGlvbkVsZW1lbnQpID0+IHtcbiAgICAgICAgICAgIGlmIChvcHRpb24uc2VsZWN0ZWQpIHtcbiAgICAgICAgICAgICAgICB2YWx1ZXMucHVzaChvcHRpb24udmFsdWUpO1xuICAgICAgICAgICAgfVxuICAgICAgICB9KTtcblxuXHR0aGlzLnByb3BzLmVudGVyRGF0YShjZGVDb2RlLCB2YWx1ZXMpO1xuICAgIH1cblxuICAgIHB1YmxpYyBoYW5kbGVDb25zZW50KGV2ZW50KSB7XG4gICAgICAgIGNvbnN0IGlzQ29uc2VudENoZWNrZWQgPSBldmVudC50YXJnZXQuY2hlY2tlZDtcbiAgICAgICAgY29uc3QgY2RlQ29kZSA9IGV2ZW50LnRhcmdldC5uYW1lO1xuICAgICAgICB0aGlzLnByb3BzLmVudGVyRGF0YShjZGVDb2RlLCBpc0NvbnNlbnRDaGVja2VkKTtcbiAgICB9XG5cbiAgICBwdWJsaWMgb25TbGlkZXJDaGFuZ2UgPSAodmFsdWUpID0+IHtcbiAgICAgICAgY29uc3QgY29kZSA9IHRoaXMucHJvcHMucXVlc3Rpb25zW3RoaXMucHJvcHMuc3RhZ2VdLmNkZTtcbiAgICAgICAgdGhpcy5wcm9wcy5lbnRlckRhdGEoY29kZSwgdmFsdWUpO1xuICAgIH1cblxuICAgIHB1YmxpYyBnZXRNYXJrcyA9IChxdWVzdGlvbikgPT4ge1xuICAgICAgICBjb25zdCBtaW5WYWx1ZSA9IHF1ZXN0aW9uLnNwZWMubWluO1xuICAgICAgICBjb25zdCBtYXhWYWx1ZSA9IHF1ZXN0aW9uLnNwZWMubWF4O1xuICAgICAgICBjb25zdCBtYXJrcyA9IHtcbiAgICAgICAgICAgIFttaW5WYWx1ZV06IDxzdHJvbmc+e21pblZhbHVlfTwvc3Ryb25nPixcbiAgICAgICAgICAgIDEwOicxMCcsXG4gICAgICAgICAgICAyMDonMjAnLFxuICAgICAgICAgICAgMzA6JzMwJyxcbiAgICAgICAgICAgIDQwOic0MCcsXG4gICAgICAgICAgICA1MDonNTAnLFxuICAgICAgICAgICAgNjA6JzYwJyxcbiAgICAgICAgICAgIDcwOic3MCcsXG4gICAgICAgICAgICA4MDonODAnLFxuICAgICAgICAgICAgOTA6JzkwJyxcbiAgICAgICAgICAgIFttYXhWYWx1ZV06IHtcbiAgICAgICAgICAgICAgICAgIHN0eWxlOiB7XG4gICAgICAgICAgICAgICAgICAgIGNvbG9yOiAncmVkJyxcbiAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICBsYWJlbDo8c3Ryb25nPnttYXhWYWx1ZX08L3N0cm9uZz4sXG4gICAgICAgICAgICAgICAgfSxcbiAgICAgICAgfTtcblxuICAgICAgICByZXR1cm4gbWFya3M7XG5cbiAgICB9XG5cbiAgICBwdWJsaWMgZ2V0U2xpZGVySGFuZGxlID0gKCkgPT4ge1xuICAgICAgICBjb25zdCBIYW5kbGUgPSBTbGlkZXIuSGFuZGxlO1xuICAgICAgICBjb25zdCBoYW5kbGUgPSBwcm9wcyA9PiB7XG4gICAgICAgICAgICBjb25zdCB7IHZhbHVlLCBkcmFnZ2luZywgaW5kZXgsIC4uLnJlc3RQcm9wcyB9ID0gcHJvcHM7XG5cbiAgICAgICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICAgICAgPFRvb2x0aXBcbiAgICAgICAgICAgICAgICAgICAgcHJlZml4Q2xzPVwicmMtc2xpZGVyLXRvb2x0aXBcIlxuICAgICAgICAgICAgICAgICAgICBvdmVybGF5PXt2YWx1ZX1cbiAgICAgICAgICAgICAgICAgICAgdmlzaWJsZT17ZHJhZ2dpbmd9XG4gICAgICAgICAgICAgICAgICAgIHBsYWNlbWVudD1cInRvcFwiXG4gICAgICAgICAgICAgICAgICAgIGtleT17aW5kZXh9XG4gICAgICAgICAgICAgICAgICAgID5cbiAgICAgICAgICAgICAgICAgICAgPEhhbmRsZSB2YWx1ZT17dmFsdWV9IHsuLi5yZXN0UHJvcHN9IC8+XG4gICAgICAgICAgICAgICAgPC9Ub29sdGlwPlxuICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICB9O1xuICAgICAgICByZXR1cm4gaGFuZGxlO1xuICAgIH1cblxuICAgIHB1YmxpYyByZW5kZXJNdWx0aVNlbGVjdChxdWVzdGlvbjogYW55KSB7XG5cdHJldHVybiAoXG5cdCAgICAgPEZvcm0+XG4gICAgICAgICAgICAgICAgPEZvcm1Hcm91cCB0YWc9XCJmaWVsZHNldFwiPlxuICAgICAgICAgICAgICAgICAgPGg2PjxpPntxdWVzdGlvbi5zdXJ2ZXlfcXVlc3Rpb25faW5zdHJ1Y3Rpb259PC9pPjwvaDY+XG4gICAgICAgICAgICAgICAgICA8aDQ+e3F1ZXN0aW9uLnRpdGxlfTwvaDQ+XG4gICAgICAgICAgICAgICAgICA8aT57cXVlc3Rpb24uaW5zdHJ1Y3Rpb25zfTwvaT5cblx0ICAgICAgICA8L0Zvcm1Hcm91cD5cblx0ICAgIDxGb3JtR3JvdXA+XG5cdCAgICA8Q29sIHNtPVwiMTJcIiBtZD17e3NpemU6Niwgb2Zmc2V0OjN9fT5cblx0ICAgIDxJbnB1dCB0eXBlPVwic2VsZWN0XCJcblx0ICAgIG5hbWU9e3F1ZXN0aW9uLmNkZX1cblx0ICAgIG9uQ2hhbmdlPXt0aGlzLmhhbmRsZU11bHRpQ2hhbmdlfSBtdWx0aXBsZT17dHJ1ZX0gPlxuXHQgICAgeyBfLm1hcChxdWVzdGlvbi5zcGVjLm9wdGlvbnMsIChvcHRpb24sIGluZGV4KSA9PiAoXG5cdFx0ICAgIDxvcHRpb24ga2V5PXtvcHRpb24uY29kZX0gdmFsdWU9e29wdGlvbi5jb2RlfT5cblx0XHQgICAge29wdGlvbi50ZXh0fVxuXHRcdCAgICA8L29wdGlvbj5cblx0ICAgICkpXG5cdCAgICB9XG4gICAgICAgICAgICA8L0lucHV0PlxuXHQgICAgPC9Db2w+XG5cdCAgICA8L0Zvcm1Hcm91cD5cblx0ICAgIDwvRm9ybT5cblx0KTtcbiAgICB9XG5cblxuICAgIHB1YmxpYyByZW5kZXIoKSB7XG4gICAgICAgIGNvbnN0IHF1ZXN0aW9uID0gdGhpcy5wcm9wcy5xdWVzdGlvbnNbdGhpcy5wcm9wcy5zdGFnZV07XG4gICAgICAgIGxldCBkZWZhdWx0VmFsdWUgPSAwO1xuICAgICAgICBpZiAocXVlc3Rpb24uc3BlYy50YWcgPT09ICdpbnRlZ2VyJykge1xuICAgICAgICAgICAgaWYodGhpcy5wcm9wcy5hbnN3ZXJzW3F1ZXN0aW9uLmNkZV0gIT09IHVuZGVmaW5lZCkge1xuICAgICAgICAgICAgICAgIGRlZmF1bHRWYWx1ZSA9IHRoaXMucHJvcHMuYW5zd2Vyc1txdWVzdGlvbi5jZGVdO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICB0aGlzLm9uU2xpZGVyQ2hhbmdlKGRlZmF1bHRWYWx1ZSk7XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgICAgY29uc3QgYm94U3R5bGUgPSB7d2lkdGg6IFwiMTAwcHhcIiwgaGVpZ2h0OlwiMTAwcHhcIiwgYmFja2dyb3VuZENvbG9yOiBcImJsYWNrXCJ9O1xuICAgICAgICBjb25zdCBwU3R5bGUgPSB7Y29sb3I6IFwid2hpdGVcIiwgYWxpZ246IFwiY2VudGVyXCJ9O1xuICAgICAgICBjb25zdCBzdHlsZSA9IHsgd2lkdGg6IFwiNTAlXCIsIGhlaWdodDpcIjUwdmhcIiwgbWFyZ2luOlwiMCBhdXRvXCIsIGxlZnRQYWRkaW5nOiBcIjEwMHB4XCIgfTtcbiAgICAgICAgY29uc3QgaXNMYXN0ID0gKHRoaXMucHJvcHMucXVlc3Rpb25zLmxlbmd0aCAtIDEpID09PSB0aGlzLnByb3BzLnN0YWdlO1xuXG4gICAgICAgIGNvbnN0IGlzQ29uc2VudCA9IHF1ZXN0aW9uLmNkZSA9PT0gXCJQUk9NU0NvbnNlbnRcIjtcbiAgICAgICAgY29uc3QgY29uc2VudFRleHQgPSA8ZGl2PkJ5IHRpY2tpbmcgdGhpcyBib3ggeW91OlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA8dWw+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA8bGk+R2l2ZSBjb25zZW50IGZvciB0aGUgaW5mb3JtYXRpb24geW91IHByb3ZpZGUgdG8gYmUgdXNlZCBmb3IgdGhlIENJQyBDYW5jZXIgcHJvamVjdDsgYW5kIDwvbGk+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA8bGk+V2lsbCByZWNlaXZlIGEgcmVtaW5kZXIgd2hlbiB0aGUgbmV4dCBzdXJ2ZXkgaXMgZHVlLjwvbGk+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDwvdWw+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgPC9kaXY+O1xuICAgICAgICBjb25zdCBpc011bHRpU2VsZWN0ID0gcXVlc3Rpb24uc3BlYy50YWcgPT09ICdyYW5nZScgJiYgcXVlc3Rpb24uc3BlYy5hbGxvd19tdWx0aXBsZTtcblxuICAgICAgICBpZiAoaXNNdWx0aVNlbGVjdCkge1xuICAgICAgICAgICAgcmV0dXJuIHRoaXMucmVuZGVyTXVsdGlTZWxlY3QocXVlc3Rpb24pO1xuICAgICAgICB9XG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIDxGb3JtPlxuICAgICAgICAgICAgICAgIDxGb3JtR3JvdXAgdGFnPVwiZmllbGRzZXRcIj5cbiAgICAgICAgICAgICAgICAgICAgPGg2PjxpPnt0aGlzLnByb3BzLnF1ZXN0aW9uc1t0aGlzLnByb3BzLnN0YWdlXS5zdXJ2ZXlfcXVlc3Rpb25faW5zdHJ1Y3Rpb259PC9pPjwvaDY+XG4gICAgICAgICAgICAgICAgICAgIDxoND57dGhpcy5wcm9wcy5xdWVzdGlvbnNbdGhpcy5wcm9wcy5zdGFnZV0udGl0bGV9PC9oND5cbiAgICAgICAgICAgICAgICAgICAgPGk+e3RoaXMucHJvcHMucXVlc3Rpb25zW3RoaXMucHJvcHMuc3RhZ2VdLmluc3RydWN0aW9uc308L2k+XG4gICAgICAgICAgICAgICAgPC9Gb3JtR3JvdXA+XG4gICAgICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgICAgICAocXVlc3Rpb24uc3BlYy50YWcgPT09ICdpbnRlZ2VyJyA/XG4gICAgICAgICAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT0ncm93Jz5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cImNvbFwiPlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cImZsb2F0LXJpZ2h0XCIgc3R5bGU9e2JveFN0eWxlfT5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDxwIGNsYXNzTmFtZT1cInRleHQtY2VudGVyXCIgc3R5bGU9e3BTdHlsZX0+WU9VUiBIRUFMVEggUkFURSBUT0RBWSA8Yj57ZGVmYXVsdFZhbHVlfTwvYj48L3A+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwiY29sXCIgc3R5bGU9e3N0eWxlfT5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPFNsaWRlciB2ZXJ0aWNhbD17dHJ1ZX0gbWluPXtxdWVzdGlvbi5zcGVjLm1pbn1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIG1heD17cXVlc3Rpb24uc3BlYy5tYXh9XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBkZWZhdWx0VmFsdWU9e2RlZmF1bHRWYWx1ZX1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIG1hcmtzPXt0aGlzLmdldE1hcmtzKHF1ZXN0aW9uKX1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGhhbmRsZT17dGhpcy5nZXRTbGlkZXJIYW5kbGUoKX1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlPXt0aGlzLm9uU2xpZGVyQ2hhbmdlfVxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAvPlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgICAgICAgICAgPC9kaXY+XG5cbiAgICAgICAgICAgICAgICAgICAgICAgIDpcblxuICAgICAgICAgICAgICAgICAgICAgICAgaXNDb25zZW50ID9cbiAgICAgICAgICAgICAgICAgICAgICAgIDxGb3JtR3JvdXAgY2hlY2s9e3RydWV9PlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIDxMYWJlbCBjaGVjaz17dHJ1ZX0+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDxJbnB1dCB0eXBlPVwiY2hlY2tib3hcIiBuYW1lPXt0aGlzLnByb3BzLnF1ZXN0aW9uc1t0aGlzLnByb3BzLnN0YWdlXS5jZGV9XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZT17dGhpcy5oYW5kbGVDb25zZW50fVxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY2hlY2tlZD17dGhpcy5wcm9wcy5hbnN3ZXJzW3F1ZXN0aW9uLmNkZV19IC8+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHtjb25zZW50VGV4dH1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICA8L0xhYmVsPlxuICAgICAgICAgICAgICAgICAgICAgICAgPC9Gb3JtR3JvdXA+XG4gICAgICAgICAgICAgICAgICAgICAgICA6XG4gICAgICAgICAgICAgICAgICAgICAgICBfLm1hcChxdWVzdGlvbi5zcGVjLnRhZz09PSdyYW5nZScgPyBxdWVzdGlvbi5zcGVjLm9wdGlvbnMgOiBbXSwgKG9wdGlvbiwgaW5kZXgpID0+IChcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICA8Rm9ybUdyb3VwIGNoZWNrPXt0cnVlfT5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPENvbCBzbT1cIjEyXCIgbWQ9e3sgc2l6ZTogNiwgb2Zmc2V0OiAzIH19PlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPExhYmVsIGNoZWNrPXt0cnVlfT5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA8SW5wdXQgdHlwZT1cInJhZGlvXCIgbmFtZT17dGhpcy5wcm9wcy5xdWVzdGlvbnNbdGhpcy5wcm9wcy5zdGFnZV0uY2RlfSB2YWx1ZT17b3B0aW9uLmNvZGV9XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlPXt0aGlzLmhhbmRsZUNoYW5nZX1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY2hlY2tlZD17b3B0aW9uLmNvZGUgPT09IHRoaXMucHJvcHMuYW5zd2Vyc1txdWVzdGlvbi5jZGVdfSAvPntvcHRpb24udGV4dH1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDwvTGFiZWw+XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDwvQ29sPlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIDwvRm9ybUdyb3VwPlxuICAgICAgICAgICAgICAgICAgICAgICAgKSlcbiAgICAgICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIDwvRm9ybT4pO1xuICAgIH1cbn1cblxuZnVuY3Rpb24gbWFwU3RhdGVUb1Byb3BzKHN0YXRlKSB7XG4gICAgcmV0dXJuIHtcbiAgICAgICAgcXVlc3Rpb25zOiBzdGF0ZS5xdWVzdGlvbnMsXG4gICAgICAgIHN0YWdlOiBzdGF0ZS5zdGFnZSxcbiAgICAgICAgYW5zd2Vyczogc3RhdGUuYW5zd2VycyxcbiAgICB9O1xufVxuXG5cbmZ1bmN0aW9uIG1hcFByb3BzVG9EaXNwYXRjaChkaXNwYXRjaCkge1xuICAgIHJldHVybiAoe1xuICAgICAgICBlbnRlckRhdGE6IChjZGVDb2RlOiBzdHJpbmcsIGNkZVZhbHVlOiBhbnkpID0+IGRpc3BhdGNoKGFjdGlvbnMuZW50ZXJEYXRhKHsgY2RlOiBjZGVDb2RlLCB2YWx1ZTogY2RlVmFsdWUgfSkpLFxuICAgIH0pO1xufVxuXG5leHBvcnQgZGVmYXVsdCBjb25uZWN0PHt9LCB7fSwgUXVlc3Rpb25JbnRlcmZhY2U+KG1hcFN0YXRlVG9Qcm9wcywgbWFwUHJvcHNUb0Rpc3BhdGNoKShRdWVzdGlvbik7XG5cblxuXG4iLCJpbXBvcnQgKiBhcyBfIGZyb20gJ2xvZGFzaCc7XG5cbmludGVyZmFjZSBFcXVhbHNDb25kaXRpb24ge1xuICAgIG9wOiAnPScsXG4gICAgY2RlOiBzdHJpbmcsXG4gICAgdmFsdWU6IGFueSxcbn1cblxuLy8gbWF5YmUgdGhpcyBpcyBlbm91Z2hcbnR5cGUgQ29uZGl0aW9uID0gRXF1YWxzQ29uZGl0aW9uO1xuXG4vLyBFbGVtZW50cyBvZiB3b3JrZmxvd1xuLy8gSSB0cmllZCB0byBtYWtlIFVuY29uZGl0aW9uYWxFbGVtZW50IGp1c3QgYSBzdHJpbmcgYnV0IGdvdCB0eXBlIGVycm9yc1xuaW50ZXJmYWNlIE9wdGlvbiB7XG4gICAgY29kZTogc3RyaW5nLFxuICAgIHRleHQ6IHN0cmluZyxcbn1cblxuaW50ZXJmYWNlIFJhbmdlRGF0YXR5cGUge1xuICAgIHRhZzogJ3JhbmdlJyxcbiAgICBvcHRpb25zOiBbT3B0aW9uXSxcbiAgICBhbGxvd19tdWx0aXBsZTogYm9vbGVhbixcbn1cblxuaW50ZXJmYWNlIEludGVnZXJEYXRhdHlwZSB7XG4gICAgdGFnOiAnaW50ZWdlcicsXG4gICAgbWF4OiBudW1iZXIsXG4gICAgbWluOiBudW1iZXIsXG59XG5cbnR5cGUgRGF0YXR5cGUgPSBSYW5nZURhdGF0eXBlIHwgSW50ZWdlckRhdGF0eXBlO1xuXG5pbnRlcmZhY2UgVW5jb25kaXRpb25hbEVsZW1lbnQgIHtcbiAgICB0YWc6ICdjZGUnLFxuICAgIGNkZTogc3RyaW5nLFxuICAgIHRpdGxlOiBzdHJpbmcsXG4gICAgaW5zdHJ1Y3Rpb25zOiBzdHJpbmcsXG4gICAgc3BlYzogRGF0YXR5cGUsXG4gICAgc3VydmV5X3F1ZXN0aW9uX2luc3RydWN0aW9uOiBzdHJpbmcsXG4gICAgY29weXJpZ2h0X3RleHQgOiBzdHJpbmcsXG4gICAgc291cmNlIDogc3RyaW5nLFxufVxuXG5pbnRlcmZhY2UgQ29uZGl0aW9uYWxFbGVtZW50IHtcbiAgICB0YWc6ICdjb25kJyxcbiAgICBjb25kOiBDb25kaXRpb24sXG4gICAgY2RlOiBzdHJpbmcsXG4gICAgdGl0bGU6IHN0cmluZyxcbiAgICBpbnN0cnVjdGlvbnM6IHN0cmluZyxcbiAgICBzcGVjOiBEYXRhdHlwZSxcbiAgICBzdXJ2ZXlfcXVlc3Rpb25faW5zdHJ1Y3Rpb246IHN0cmluZyxcbiAgICBjb3B5cmlnaHRfdGV4dCA6IHN0cmluZyxcbiAgICBzb3VyY2UgOiBzdHJpbmcsXG59XG5cbnR5cGUgRWxlbWVudCA9IFVuY29uZGl0aW9uYWxFbGVtZW50IHwgQ29uZGl0aW9uYWxFbGVtZW50O1xuXG5leHBvcnQgdHlwZSBFbGVtZW50TGlzdCA9IFtFbGVtZW50XTtcblxuZnVuY3Rpb24gZXZhbENvbmRpdGlvbihjb25kOiBDb25kaXRpb24sIHN0YXRlOiBhbnkpOiBib29sZWFuIHtcbiAgICAvLyBFdmFsdWF0ZXMgYSBjb25kaXRpb25hbCBlbGVtZW50IGluIHRoZSBjdXJyZW50IHN0YXRlXG4gICAgLy8gV2Ugb25seSBzaG93IGFwcGxpY2FibGUgcXVlc3Rpb25zIC0gaS5lLiB0aG9zZVxuICAgIC8vIHdoaWNoIGV2YWx1YXRlIHRvIHRydWVcbiAgICBpZiAoc3RhdGUuYW5zd2Vycy5oYXNPd25Qcm9wZXJ0eShjb25kLmNkZSkpIHtcbiAgICBjb25zdCBhbnN3ZXIgPSBzdGF0ZS5hbnN3ZXJzW2NvbmQuY2RlXTtcblx0c3dpdGNoIChjb25kLm9wKSB7XG5cdCAgICBjYXNlICc9Jzpcblx0XHRyZXR1cm4gYW5zd2VyID09PSBjb25kLnZhbHVlO1xuICAgICAgICAgICAgZGVmYXVsdDpcblx0XHRyZXR1cm4gZmFsc2U7IC8vIGV4dGVuZCB0aGlzIGxhdGVyXG5cdH1cbiAgICB9XG4gICAgZWxzZSB7XG5cdHJldHVybiBmYWxzZTtcbiAgICB9XG59XG4gICAgXG5cbmZ1bmN0aW9uIGV2YWxFbGVtZW50KGVsOkVsZW1lbnQsIHN0YXRlOiBhbnkpOiBib29sZWFuIHtcbiAgICBzd2l0Y2goZWwudGFnKSB7XG5cdGNhc2UgJ2NkZSc6XG5cdCAgICAvLyBVbmNvbmRpdGlvbmFsIGVsZW1lbnRzIGFyZSBhbHdheXMgc2hvd25cblx0ICAgIHJldHVybiB0cnVlO1xuXHRjYXNlICdjb25kJzpcblx0ICAgIC8vIGNvbmRpdGlvbmFsIGVsZW1lbnRzIGRlcGVuZCB0aGVpciBhc3NvY2lhdGVkXG5cdCAgICAvLyBjb25kaXRpb24gYmVpbmcgdHJ1ZVxuXHQgICAgcmV0dXJuIGV2YWxDb25kaXRpb24oZWwuY29uZCwgc3RhdGUpO1xuXHRkZWZhdWx0OlxuXHQgICAgcmV0dXJuIGZhbHNlO1xuICAgIH1cbn1cblxuXG5leHBvcnQgZnVuY3Rpb24gZXZhbEVsZW1lbnRzKGVsZW1lbnRzOiBFbGVtZW50W10sIHN0YXRlOmFueSk6IEVsZW1lbnRbXSB7XG4gICAgLy8gVGhlIHF1ZXN0aW9ucyB0byBzaG93IGF0IGFueSB0aW1lIGFyZSB0aG9zZSB3aG9zZSBwcmVjb25kaXRpb25zXG4gICAgLy8gYXJlIGZ1bGZpbGxlZFxuICAgIHJldHVybiBlbGVtZW50cy5maWx0ZXIoZWwgPT4gZXZhbEVsZW1lbnQoZWwsIHN0YXRlKSk7XG59XG4gXG4iLCJpbXBvcnQgYXhpb3MgZnJvbSAnYXhpb3MnO1xuaW1wb3J0IHsgY3JlYXRlQWN0aW9uLCBoYW5kbGVBY3Rpb25zIH0gZnJvbSAncmVkdXgtYWN0aW9ucyc7XG5cbmV4cG9ydCBjb25zdCBnb1ByZXZpb3VzID0gY3JlYXRlQWN0aW9uKFwiUFJPTVNfUFJFVklPVVNcIik7XG5leHBvcnQgY29uc3QgZ29OZXh0ID0gY3JlYXRlQWN0aW9uKFwiUFJPTVNfTkVYVFwiKTtcbmV4cG9ydCBjb25zdCBzdWJtaXRBbnN3ZXJzID0gY3JlYXRlQWN0aW9uKFwiUFJPTVNfU1VCTUlUXCIpO1xuZXhwb3J0IGNvbnN0IGVudGVyRGF0YSA9IGNyZWF0ZUFjdGlvbihcIlBST01TX0VOVEVSX0RBVEFcIik7XG5cbmltcG9ydCB7IGV2YWxFbGVtZW50cyB9IGZyb20gJy4uL2xvZ2ljJztcblxuXG5heGlvcy5kZWZhdWx0cy54c3JmSGVhZGVyTmFtZSA9IFwiWC1DU1JGVE9LRU5cIjtcbmF4aW9zLmRlZmF1bHRzLnhzcmZDb29raWVOYW1lID0gXCJjc3JmdG9rZW5cIjtcblxuZnVuY3Rpb24gc3VibWl0U3VydmV5KGFuc3dlcnM6IHsgW2luZGV4OiBzdHJpbmddOiBzdHJpbmcgfSkge1xuICAgIGNvbnN0IHBhdGllbnRfdG9rZW46IHN0cmluZyA9IHdpbmRvdy5wcm9tc19jb25maWcucGF0aWVudF90b2tlbjtcbiAgICBjb25zdCByZWdpc3RyeV9jb2RlOiBzdHJpbmcgPSB3aW5kb3cucHJvbXNfY29uZmlnLnJlZ2lzdHJ5X2NvZGU7XG4gICAgY29uc3Qgc3VydmV5X25hbWU6IHN0cmluZyA9IHdpbmRvdy5wcm9tc19jb25maWcuc3VydmV5X25hbWU7XG4gICAgY29uc3Qgc3VydmV5RW5kcG9pbnQ6IHN0cmluZyA9IHdpbmRvdy5wcm9tc19jb25maWcuc3VydmV5X2VuZHBvaW50O1xuICAgIGNvbnN0IGRhdGEgPSB7XG4gICAgICAgIHBhdGllbnRfdG9rZW4sXG4gICAgICAgIHJlZ2lzdHJ5X2NvZGUsXG4gICAgICAgIHN1cnZleV9uYW1lLFxuICAgICAgICBhbnN3ZXJzXG4gICAgfTtcbiAgICBheGlvcy5wb3N0KHN1cnZleUVuZHBvaW50LCBkYXRhKVxuICAgICAgICAudGhlbihyZXMgPT4gd2luZG93LmxvY2F0aW9uLnJlcGxhY2Uod2luZG93LnByb21zX2NvbmZpZy5jb21wbGV0ZWRfcGFnZSkpXG4gICAgICAgIC5jYXRjaChlcnIgPT4gYWxlcnQoZXJyLnRvU3RyaW5nKCkpKTtcbn1cblxuY29uc3QgaW5pdGlhbFN0YXRlID0ge1xuICAgIHN0YWdlOiAwLFxuICAgIGFuc3dlcnM6IHt9LFxuICAgIHF1ZXN0aW9uczogZXZhbEVsZW1lbnRzKHdpbmRvdy5wcm9tc19jb25maWcucXVlc3Rpb25zLCB7IGFuc3dlcnM6IHt9IH0pLFxuICAgIHRpdGxlOiAnJyxcbn1cblxuZnVuY3Rpb24gaXNDb25kKHN0YXRlKSB7XG4gICAgY29uc3Qgc3RhZ2UgPSBzdGF0ZS5zdGFnZTtcbiAgICByZXR1cm4gc3RhdGUucXVlc3Rpb25zW3N0YWdlXS50YWcgPT09ICdjb25kJztcbn1cblxuXG5mdW5jdGlvbiB1cGRhdGVBbnN3ZXJzKGFjdGlvbjogYW55LCBzdGF0ZTogYW55KTogYW55IHtcbiAgICAvLyBpZiBkYXRhIGVudGVyZWQgLCB1cGRhdGUgdGhlIGFuc3dlcnMgb2JqZWN0XG4gICAgY29uc3QgY2RlQ29kZSA9IGFjdGlvbi5wYXlsb2FkLmNkZTtcbiAgICBjb25zdCBuZXdWYWx1ZSA9IGFjdGlvbi5wYXlsb2FkLnZhbHVlO1xuICAgIGNvbnN0IG9sZEFuc3dlcnMgPSBzdGF0ZS5hbnN3ZXJzO1xuICAgIGNvbnN0IG5ld0Fuc3dlcnMgPSB7IC4uLm9sZEFuc3dlcnMgfTtcbiAgICBuZXdBbnN3ZXJzW2NkZUNvZGVdID0gbmV3VmFsdWU7XG4gICAgcmV0dXJuIG5ld0Fuc3dlcnM7XG59XG5cbmZ1bmN0aW9uIGNsZWFyQW5zd2VyT25Td2lwZUJhY2soc3RhdGU6IGFueSk6IGFueSB7XG4gICAgLy8gY2xlYXIgdGhlIGFuc3dlciB3aGVuIG1vdmUgdG8gcHJldmlvdXMgcXVlc3Rpb25cbiAgICBjb25zdCBzdGFnZSA9IHN0YXRlLnN0YWdlO1xuICAgIGNvbnN0IHF1ZXN0aW9uQ29kZSA9IHN0YXRlLnF1ZXN0aW9uc1tzdGFnZV0uY2RlO1xuICAgIGNvbnN0IG9sZEFuc3dlcnMgPSBzdGF0ZS5hbnN3ZXJzO1xuICAgIGNvbnN0IG5ld0Fuc3dlcnMgPSB7IC4uLm9sZEFuc3dlcnMgfTtcbiAgICBkZWxldGUgbmV3QW5zd2Vyc1txdWVzdGlvbkNvZGVdO1xuICAgIHJldHVybiBuZXdBbnN3ZXJzO1xufVxuXG5mdW5jdGlvbiB1cGRhdGVDb25zZW50KHN0YXRlOiBhbnkpOiBhbnkge1xuICAgIGNvbnN0IHF1ZXN0aW9uQ291bnQgPSBzdGF0ZS5xdWVzdGlvbnMubGVuZ3RoO1xuICAgIGNvbnN0IGFsbEFuc3dlcnMgPSBzdGF0ZS5hbnN3ZXJzO1xuICAgIGNvbnN0IHF1ZXN0aW9uQ29kZSA9IHN0YXRlLnF1ZXN0aW9uc1txdWVzdGlvbkNvdW50IC0gMV0uY2RlO1xuICAgIGlmICghYWxsQW5zd2Vycy5oYXNPd25Qcm9wZXJ0eShxdWVzdGlvbkNvZGUpKSB7XG4gICAgICAgIGNvbnN0IG9sZEFuc3dlcnMgPSBzdGF0ZS5hbnN3ZXJzO1xuICAgICAgICBjb25zdCBuZXdBbnN3ZXJzID0geyAuLi5vbGRBbnN3ZXJzIH07XG4gICAgICAgIG5ld0Fuc3dlcnNbcXVlc3Rpb25Db2RlXSA9IGZhbHNlO1xuICAgICAgICByZXR1cm4gbmV3QW5zd2VycztcbiAgICB9XG5cbiAgICByZXR1cm4gYWxsQW5zd2Vycztcbn1cblxuZXhwb3J0IGNvbnN0IHByb21zUGFnZVJlZHVjZXIgPSBoYW5kbGVBY3Rpb25zKHtcbiAgICBbZ29QcmV2aW91cyBhcyBhbnldOlxuICAgICAgICAoc3RhdGUsIGFjdGlvbjogYW55KSA9PiAoe1xuICAgICAgICAgICAgLi4uc3RhdGUsXG4gICAgICAgICAgICBhbnN3ZXJzOiBjbGVhckFuc3dlck9uU3dpcGVCYWNrKHN0YXRlKSxcbiAgICAgICAgICAgIHN0YWdlOiBzdGF0ZS5zdGFnZSAtIDEsXG4gICAgICAgIH0pLFxuICAgIFtnb05leHQgYXMgYW55XTpcbiAgICAgICAgKHN0YXRlLCBhY3Rpb246IGFueSkgPT4gKHtcbiAgICAgICAgICAgIC4uLnN0YXRlLFxuICAgICAgICAgICAgc3RhZ2U6IHN0YXRlLnN0YWdlICsgMSxcbiAgICAgICAgfSksXG4gICAgW3N1Ym1pdEFuc3dlcnMgYXMgYW55XTpcbiAgICAgICAgKHN0YXRlLCBhY3Rpb246IGFueSkgPT4ge1xuICAgICAgICAgICAgY29uc3QgbmV3U3RhdGUgPSB7XG4gICAgICAgICAgICAgICAgLi4uc3RhdGUsXG4gICAgICAgICAgICAgICAgYW5zd2VyczogdXBkYXRlQ29uc2VudChzdGF0ZSksXG4gICAgICAgICAgICB9O1xuICAgICAgICAgICAgc3VibWl0U3VydmV5KG5ld1N0YXRlLmFuc3dlcnMpO1xuICAgICAgICAgICAgcmV0dXJuIG5ld1N0YXRlO1xuICAgICAgICB9LFxuICAgIFtlbnRlckRhdGEgYXMgYW55XTpcbiAgICAgICAgKHN0YXRlLCBhY3Rpb24pID0+IHtcbiAgICAgICAgICAgIGNvbnN0IHVwZGF0ZWRBbnN3ZXJzID0gdXBkYXRlQW5zd2VycyhhY3Rpb24sIHN0YXRlKVxuICAgICAgICAgICAgY29uc3QgbmV3U3RhdGUgPSB7XG4gICAgICAgICAgICAgICAgLi4uc3RhdGUsXG4gICAgICAgICAgICAgICAgYW5zd2VyczogdXBkYXRlQW5zd2VycyhhY3Rpb24sIHN0YXRlKSxcbiAgICAgICAgICAgICAgICBxdWVzdGlvbnM6IGV2YWxFbGVtZW50cyh3aW5kb3cucHJvbXNfY29uZmlnLnF1ZXN0aW9ucywgeyBhbnN3ZXJzOiB1cGRhdGVkQW5zd2VycyB9KSxcbiAgICAgICAgICAgIH07XG4gICAgICAgICAgICByZXR1cm4gbmV3U3RhdGU7XG4gICAgICAgIH0sXG59LCBpbml0aWFsU3RhdGUpO1xuIl0sInNvdXJjZVJvb3QiOiIifQ==