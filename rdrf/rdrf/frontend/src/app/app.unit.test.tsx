import * as React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { applyMiddleware, compose, createStore } from "redux";
import thunk from "redux-thunk";
import moxios from "moxios";
import * as actions from "../pages/proms_page/reducers";
import App from "./index";

const devtoolsExtension = "__REDUX_DEVTOOLS_EXTENSION_COMPOSE__";
const composeEnhancers = window[devtoolsExtension] || compose;

/*
const unsubscribe = testStore.subscribe(() =>
  global.console.log(testStore.getState())
);
*/

const regQ1String = "registryQ1";
const regQ4String = "registryQ4";
const regQ5String = "registryQ5";

let actionList = [];
const captureAction = state => next => action => {
  actionList.push(action);
  return next(action);
};

describe("An empty App component", () => {
  // const newApp = <App />;
  // Constructed like this because of the way App is exported - the class is wrapped
  const newApp = new App.WrappedComponent({});
  it("is defined", () => {
    // stuff goes here
    expect(newApp).toBeDefined();
  });
  it("has empty properties", () => {
    expect(newApp).toHaveProperty("props");
    expect(newApp.props).toStrictEqual({});
  });
  it("does not have questions", () => {
    expect(newApp.props.questions).not.toBeDefined();
  });
  it("throws an error in atEnd", () => {
    expect(() => {
      newApp.atEnd();
    }).toThrow();
  });
  it("throws an error in getProgress", () => {
    expect(() => {
      newApp.getProgress();
    }).toThrow();
  });
  it("throws an error in movePrevious", () => {
    expect(() => {
      newApp.movePrevious();
    }).toThrow();
  });
  it("throws an error in moveNext", () => {
    expect(() => {
      newApp.moveNext();
    }).toThrow();
  });
  it("throws an error in render", () => {
    expect(() => {
      newApp.render();
    }).toThrow();
  });
  it("does not throw an error in atBeginning", () => {
    expect(() => {
      // atBeginning is interesting - doesn't throw an exception
      // No assignment of variables within the function
      // Only comparison between props.stage (which is undefined) and 0
      newApp.atBeginning();
    }).not.toThrow();
  });
});

/*
* Both of the following test sections update the state by directly firing actions
* on the Redux store. The alternative is to use the React Testing Library module
* fireEvent, simulating actually interacting with the page. Those tests can be set
* up later.
*/

// Checking that the component is updating correctly
describe("Component tests: A test App using Redux", () => {
  const testStore = createStore(
    actions.promsPageReducer,
    composeEnhancers(applyMiddleware(thunk, captureAction))
  );

  beforeEach(() => {
    actionList = [];
  });

  describe("Basic tests", () => {
      /*
      * Test 1 - Basic mock render
      */
      it("can render", () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
      });

      /*
      * Test 2 - Initialisation test
      */
      it("is on the first question", () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(asFragment()).toMatchInlineSnapshot(`
          <DocumentFragment>
            <div
              class="App"
              style="height: 100%;"
            >
              <div
                class="container"
              >
                <div
                  class="mb-4"
                >
                  <div
                    class="row"
                  >
                    <div
                      class="col"
                    >
                      <div
                        class="instruction"
                      />
                    </div>
                  </div>
                  <div
                    class="row"
                  >
                    <div
                      class="col"
                    >
                      <form
                        class=""
                      >
                        <fieldset
                          class="form-group"
                        >
                          <div
                            class="col-sm-12 col-md-6 offset-md-3"
                          >
                            <h6 />
                            <h4>
                              Question 1 - title
                            </h4>
                            <h6 />
                          </div>
                        </fieldset>
                        <div
                          class="form-check"
                        >
                          <div
                            class="col-sm-12 col-md-6 offset-md-3"
                          >
                            <label
                              class="form-check-label"
                            >
                              <input
                                class="form-check-input"
                                name="registryQ1"
                                type="radio"
                                value="answer1"
                              />
                              Answer 1
                            </label>
                          </div>
                        </div>
                        <div
                          class="form-check"
                        >
                          <div
                            class="col-sm-12 col-md-6 offset-md-3"
                          >
                            <label
                              class="form-check-label"
                            >
                              <input
                                class="form-check-input"
                                name="registryQ1"
                                type="radio"
                                value="answer2"
                              />
                              Answer 2
                            </label>
                          </div>
                        </div>
                      </form>
                    </div>
                  </div>
                </div>
                <div
                  class="mb-4"
                >
                  <div
                    class="navigationinputs row"
                  >
                    <div
                      class="col-sm-2"
                      style="display: flex;"
                    >
                      <button
                        class="btn btn-info btn-sm disabled"
                        disabled=""
                        style="min-width: 90px;"
                        type="button"
                      >
                        Previous
                      </button>
                    </div>
                    <div
                      class="col-sm-8"
                    >
                      <div
                        class="progress"
                      >
                        <div
                          aria-valuemax="100"
                          aria-valuemin="0"
                          aria-valuenow="0"
                          class="progress-bar bg-info"
                          role="progressbar"
                          style="width: 0%;"
                        >
                          0%
                        </div>
                      </div>
                    </div>
                    <div
                      class="col-sm-2"
                      style="display: flex; justify-content: flex-end;"
                    >
                      <button
                        class="btn btn-info btn-sm"
                        style="min-width: 90px;"
                        type="button"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <footer
                class="footer"
                style="height: auto;"
              >
                <div
                  class="text-center text-muted"
                  style="font-size: 12px;"
                />
              </footer>
            </div>
          </DocumentFragment>
        `);
        expect(testStore.getState().stage).toEqual(0);
        expect(screen.getByText("Question", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("1")
        );
        expect(screen.getByText("Previous").disabled).toEqual(true);
      });

      /*
      * Test 3 - Next question test
      */
      it('can go to the next question from the first question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("Question", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("1")
        );

        // testStore.dispatch(actions.goNext());
        const nextButton = screen.getByText("Next");
        fireEvent.click(nextButton);

        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("Question", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("2")
        );
      });

      /*
      * Test 4 - Previous question test
      */
      it('can go to the previous question from the second question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("Question", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("2")
        );

        testStore.dispatch(actions.goPrevious());

        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("Question", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("1")
        );
      });
  });

  describe("Preconditional tests: 'or'", () => {
      /*
      * Test 5
      */
      it('only has three questions', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("Question", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("1")
        );
        expect(screen.getByText("Previous").disabled).toEqual(true);
        expect(screen.getByText("Next").disabled).toEqual(false);
        expect(testStore.getState().stage).toEqual(0);

        // Change to clicking Next button?
        testStore.dispatch(actions.goNext());

        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("Question", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("2")
        );
        expect(screen.getByText("Previous").disabled).toEqual(false);
        expect(screen.getByText("Next").disabled).toEqual(false);
        expect(testStore.getState().stage).toEqual(1);

        testStore.dispatch(actions.goNext());

        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("Consent")).toBeDefined();
        expect(screen.getByText("Previous").disabled).toEqual(false);
        expect(() => {
          screen.getByText("Next");
        }).toThrow();
        expect(screen.getByText("Submit", { exact: false })).toBeDefined();
        expect(testStore.getState().stage).toEqual(2);
      });

      /*
      * Test 6
      */
      it('can have data entered', () => {
        testStore.getState().stage = 0;

        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        const answer1Select = screen.getByLabelText("Answer 1", { exact: false });
        expect(answer1Select.checked).toEqual(false);
        
        // Unsure which to use - both work
        fireEvent.click(answer1Select);
        // testStore.dispatch(actions.enterData({cde: "registryQ1", value: "answer1", isValid: true}));

        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(answer1Select.checked).toEqual(true);
        expect(testStore.getState().answers).toHaveProperty("registryQ1");
      });

      /*
      * Test 7
      */
      it('has the third question (preconditional) available after entering data in the first question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 1")
        );
        expect(screen.getByText("Previous").disabled).toEqual(true);
        const nextButton = screen.getByText("Next");
        expect(nextButton.disabled).toEqual(false);
        expect(testStore.getState().stage).toEqual(0);

        // Change to clicking Next button?
        // testStore.dispatch(actions.goNext());
        fireEvent.click(nextButton);

        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 2")
        );
        expect(screen.getByText("Previous").disabled).toEqual(false);
        expect(nextButton.disabled).toEqual(false);
        expect(testStore.getState().stage).toEqual(1);

        // testStore.dispatch(actions.goNext());
        fireEvent.click(nextButton);

        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 3")
        );
        expect(screen.getByText("Previous").disabled).toEqual(false);
        expect(nextButton.disabled).toEqual(false);
        expect(testStore.getState().stage).toEqual(2);

        // testStore.dispatch(actions.goNext());
        fireEvent.click(nextButton);

        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(screen.getByText("Consent")).toBeDefined();
        expect(screen.getByText("Previous").disabled).toEqual(false);
        expect(() => {
          screen.getByText("Next");
        }).toThrow();
        // expect(screen.getByText("Submit", { exact: false })).toBeDefined();
        expect(nextButton.innerHTML).toEqual(expect.stringContaining("Submit"));
        expect(testStore.getState().stage).toEqual(3);
      });

      /*
      * Test 8
      */
      it('has the third question remain available after changing data in the first question', () => {
        // Start at Question 1
        testStore.getState().stage = 0;
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        let answer1Select = screen.getByLabelText("Answer 1", { exact: false });
        let answer2Select = screen.getByLabelText("Answer 2", { exact: false });
        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");

        // We expect Answer 1 to be selected from Test 6
        expect(answer1Select.checked).toEqual(true);
        expect(answer2Select.checked).toEqual(false);

        // Got to next question and rerender
        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        // Ditto
        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        // We should be on Question 3 as precondition is met
        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 3")
        );

        // Go back to Question 1
        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        // Select Answer 2 instead of Answer 1
        answer1Select = screen.getByLabelText("Answer 1", { exact: false });
        answer2Select = screen.getByLabelText("Answer 2", { exact: false });
        fireEvent.click(answer2Select);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        // We expect Answer 1 to be unchecked now - allow_multiple is false
        expect(answer1Select.checked).toEqual(false);
        expect(answer2Select.checked).toEqual(true);
        expect(testStore.getState().answers[regQ1String]).not.toEqual("answer1");

        // Go forward two questions again
        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        // We should still be able to access Question 3
        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 3")
        );
      });
  });

  describe("Preconditional tests: '='", () => {
      /*
      * Test 9
      */
      it('does not make the fourth question available if "Good" is answered in the third question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 3")
        );
        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let goodAnswerSelect = screen.getByLabelText("Good");
        let notGoodSelect = screen.getByLabelText("Not so good");
        let badAnswerSelect = screen.getByLabelText("Bad");

        expect(goodAnswerSelect.checked).toEqual(false);
        expect(notGoodSelect.checked).toEqual(false);
        expect(badAnswerSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 3")
        );
        goodAnswerSelect = screen.getByLabelText("Good");
        notGoodSelect = screen.getByLabelText("Not so good");
        badAnswerSelect = screen.getByLabelText("Bad");

        fireEvent.click(goodAnswerSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(goodAnswerSelect.checked).toEqual(true);
        expect(notGoodSelect.checked).toEqual(false);
        expect(badAnswerSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();
        // Return to Question 3 for next test
        fireEvent.click(prevButton);
      });

      /*
      * Test 10
      */
      it('does not make the fourth question available if "Not so good" is answered in the third question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 3")
        );
        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let goodAnswerSelect = screen.getByLabelText("Good");
        let notGoodSelect = screen.getByLabelText("Not so good");
        let badAnswerSelect = screen.getByLabelText("Bad");

        expect(goodAnswerSelect.checked).toEqual(true);
        expect(notGoodSelect.checked).toEqual(false);
        expect(badAnswerSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 3")
        );
        goodAnswerSelect = screen.getByLabelText("Good");
        notGoodSelect = screen.getByLabelText("Not so good");
        badAnswerSelect = screen.getByLabelText("Bad");

        fireEvent.click(notGoodSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(goodAnswerSelect.checked).toEqual(false);
        expect(notGoodSelect.checked).toEqual(true);
        expect(badAnswerSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();
        // Return to Question 3 for next test
        fireEvent.click(prevButton);
      });

      /*
      * Test 11
      */
      it('makes the fourth question available if "Bad" is answered in the third question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 3")
        );
        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let goodAnswerSelect = screen.getByLabelText("Good");
        let notGoodSelect = screen.getByLabelText("Not so good");
        let badAnswerSelect = screen.getByLabelText("Bad");

        expect(goodAnswerSelect.checked).toEqual(false);
        expect(notGoodSelect.checked).toEqual(true);
        expect(badAnswerSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 3")
        );
        goodAnswerSelect = screen.getByLabelText("Good");
        notGoodSelect = screen.getByLabelText("Not so good");
        badAnswerSelect = screen.getByLabelText("Bad");

        fireEvent.click(badAnswerSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        expect(goodAnswerSelect.checked).toEqual(false);
        expect(notGoodSelect.checked).toEqual(false);
        expect(badAnswerSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );
      });
  });

  describe("Preconditional tests: 'contains'", () => {
      /*
      * Test 12
      */
      it('does not make the fifth question available if "Work is stressful" is selected in the fourth question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );

        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let workSelect = screen.getByLabelText("Work is stressful");
        let friendsSelect = screen.getByLabelText("Can't see my friends");
        let reactSelect = screen.getByLabelText("React is difficult");
        let daySelect = screen.getByLabelText("Just a bad day");

        expect(workSelect.checked).toEqual(false);
        expect(friendsSelect.checked).toEqual(false);
        expect(reactSelect.checked).toEqual(false);
        expect(daySelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );
        workSelect = screen.getByLabelText("Work is stressful");
        friendsSelect = screen.getByLabelText("Can't see my friends");
        reactSelect = screen.getByLabelText("React is difficult");
        daySelect = screen.getByLabelText("Just a bad day");

        fireEvent.click(workSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(workSelect.checked).toEqual(true);
        expect(friendsSelect.checked).toEqual(false);
        expect(reactSelect.checked).toEqual(false);
        expect(daySelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();
        // Return to Question 4 for next test
        fireEvent.click(prevButton);
      });

      /*
      * Test 13
      */
      it('does not make the fifth question available if "Work is stressful" and "Can\'t see my friends" are selected in the fourth question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );

        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let workSelect = screen.getByLabelText("Work is stressful");
        let friendsSelect = screen.getByLabelText("Can't see my friends");
        let reactSelect = screen.getByLabelText("React is difficult");
        let daySelect = screen.getByLabelText("Just a bad day");

        expect(workSelect.checked).toEqual(true);
        expect(friendsSelect.checked).toEqual(false);
        expect(reactSelect.checked).toEqual(false);
        expect(daySelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );
        workSelect = screen.getByLabelText("Work is stressful");
        friendsSelect = screen.getByLabelText("Can't see my friends");
        reactSelect = screen.getByLabelText("React is difficult");
        daySelect = screen.getByLabelText("Just a bad day");

        fireEvent.click(friendsSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(workSelect.checked).toEqual(true);
        expect(friendsSelect.checked).toEqual(true);
        expect(reactSelect.checked).toEqual(false);
        expect(daySelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();
        // Return to Question 4 for next test
        fireEvent.click(prevButton);
      });

      /*
      * Test 14
      */
      it('does not make the fifth question available if "Can\'t see my friends" and "Just a bad day" are selected in the fourth question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );

        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let workSelect = screen.getByLabelText("Work is stressful");
        let friendsSelect = screen.getByLabelText("Can't see my friends");
        let reactSelect = screen.getByLabelText("React is difficult");
        let daySelect = screen.getByLabelText("Just a bad day");

        expect(workSelect.checked).toEqual(true);
        expect(friendsSelect.checked).toEqual(true);
        expect(reactSelect.checked).toEqual(false);
        expect(daySelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );
        workSelect = screen.getByLabelText("Work is stressful");
        friendsSelect = screen.getByLabelText("Can't see my friends");
        reactSelect = screen.getByLabelText("React is difficult");
        daySelect = screen.getByLabelText("Just a bad day");

        fireEvent.click(workSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(daySelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(workSelect.checked).toEqual(false);
        expect(friendsSelect.checked).toEqual(true);
        expect(reactSelect.checked).toEqual(false);
        expect(daySelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();
        // Return to Question 4 for next test
        fireEvent.click(prevButton);
      });

      /*
      * Test 15
      */
      it('makes the fifth question available if "React is difficult" is selected in the fourth question with other answers', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );

        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let workSelect = screen.getByLabelText("Work is stressful");
        let friendsSelect = screen.getByLabelText("Can't see my friends");
        let reactSelect = screen.getByLabelText("React is difficult");
        let daySelect = screen.getByLabelText("Just a bad day");

        expect(workSelect.checked).toEqual(false);
        expect(friendsSelect.checked).toEqual(true);
        expect(reactSelect.checked).toEqual(false);
        expect(daySelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );
        workSelect = screen.getByLabelText("Work is stressful");
        friendsSelect = screen.getByLabelText("Can't see my friends");
        reactSelect = screen.getByLabelText("React is difficult");
        daySelect = screen.getByLabelText("Just a bad day");

        fireEvent.click(reactSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(workSelect.checked).toEqual(false);
        expect(friendsSelect.checked).toEqual(true);
        expect(reactSelect.checked).toEqual(true);
        expect(daySelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );
        workSelect = screen.getByLabelText("Work is stressful");
        friendsSelect = screen.getByLabelText("Can't see my friends");
        reactSelect = screen.getByLabelText("React is difficult");
        daySelect = screen.getByLabelText("Just a bad day");

        fireEvent.click(friendsSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(workSelect.checked).toEqual(false);
        expect(friendsSelect.checked).toEqual(false);
        expect(reactSelect.checked).toEqual(true);
        expect(daySelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );
        workSelect = screen.getByLabelText("Work is stressful");
        friendsSelect = screen.getByLabelText("Can't see my friends");
        reactSelect = screen.getByLabelText("React is difficult");
        daySelect = screen.getByLabelText("Just a bad day");

        fireEvent.click(workSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(workSelect.checked).toEqual(true);
        expect(friendsSelect.checked).toEqual(false);
        expect(reactSelect.checked).toEqual(true);
        expect(daySelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 4")
        );
        workSelect = screen.getByLabelText("Work is stressful");
        friendsSelect = screen.getByLabelText("Can't see my friends");
        reactSelect = screen.getByLabelText("React is difficult");
        daySelect = screen.getByLabelText("Just a bad day");

        fireEvent.click(workSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(daySelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(workSelect.checked).toEqual(false);
        expect(friendsSelect.checked).toEqual(false);
        expect(reactSelect.checked).toEqual(true);
        expect(daySelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
      });
  });

  describe("Preconditional tests: 'intersection'", () => {
      it('does not make the sixth question available if "It\'s hard to read" is selected in the fifth question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );

        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let hardToReadSelect = screen.getByLabelText("It's hard to read");
        let dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        let facebookSelect = screen.getByLabelText("It's made by Facebook");
        let noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        expect(hardToReadSelect.checked).toEqual(false);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(hardToReadSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();
        // Return to Question 5 for next test
        fireEvent.click(prevButton);
      });

      it('does not make the sixth question available if "It\'s hard to read" and "I don\'t understand it" are selected in the fifth question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );

        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let hardToReadSelect = screen.getByLabelText("It's hard to read");
        let dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        let facebookSelect = screen.getByLabelText("It's made by Facebook");
        let noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(noUnderstandingSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();
        // Return to Question 5 for next test
        fireEvent.click(prevButton);
      });

      it('makes the sixth question available if "It has too many dependencies" is selected with any other answer in the fifth question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );

        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let hardToReadSelect = screen.getByLabelText("It's hard to read");
        let dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        let facebookSelect = screen.getByLabelText("It's made by Facebook");
        let noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(dependenciesSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(true);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 6")
        );

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(hardToReadSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(false);
        expect(dependenciesSelect.checked).toEqual(true);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 6")
        );

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(noUnderstandingSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(false);
        expect(dependenciesSelect.checked).toEqual(true);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 6")
        );

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(dependenciesSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(hardToReadSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(noUnderstandingSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();
        // Return to Question 5 for next test
        fireEvent.click(prevButton);
      });

      it('makes the sixth question available if "It\'s made by Facebook" is selected with any other answer in the fifth question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );

        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let hardToReadSelect = screen.getByLabelText("It's hard to read");
        let dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        let facebookSelect = screen.getByLabelText("It's made by Facebook");
        let noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(facebookSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(true);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 6")
        );

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(hardToReadSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(false);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(true);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 6")
        );

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(noUnderstandingSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(false);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(true);
        expect(noUnderstandingSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 6")
        );

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(facebookSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(hardToReadSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(noUnderstandingSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();
        // Return to Question 5 for next test
        fireEvent.click(prevButton);
      });

      it('makes the sixth question available if "It has too many dependencies" and "It\'s made by Facebook" are selected in the fifth question', () => {
        const { rerender, asFragment } = render(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );

        const nextButton = screen.getByText("Next");
        const prevButton = screen.getByText("Previous");
        let hardToReadSelect = screen.getByLabelText("It's hard to read");
        let dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        let facebookSelect = screen.getByLabelText("It's made by Facebook");
        let noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        expect(hardToReadSelect.checked).toEqual(true);
        expect(dependenciesSelect.checked).toEqual(false);
        expect(facebookSelect.checked).toEqual(false);
        expect(noUnderstandingSelect.checked).toEqual(true);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("Consent")).toBeDefined();

        fireEvent.click(prevButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 5")
        );
        hardToReadSelect = screen.getByLabelText("It's hard to read");
        dependenciesSelect = screen.getByLabelText("It has too many dependencies");
        facebookSelect = screen.getByLabelText("It's made by Facebook");
        noUnderstandingSelect = screen.getByLabelText("I don't understand it");

        fireEvent.click(dependenciesSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(facebookSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(hardToReadSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );
        fireEvent.click(noUnderstandingSelect);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(hardToReadSelect.checked).toEqual(false);
        expect(dependenciesSelect.checked).toEqual(true);
        expect(facebookSelect.checked).toEqual(true);
        expect(noUnderstandingSelect.checked).toEqual(false);

        fireEvent.click(nextButton);
        rerender(
          <Provider store={testStore}>
            <App />
          </Provider>
        );

        expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
          expect.stringContaining("Question 6")
        );
      });
  });

  describe('Datatype tests: integer', () => {
    it('displays a textbox in Question 7', () => {
      testStore.dispatch(actions.enterData({cde: "registryQ6", value: "typetest", isValid: true}));
      testStore.getState().stage = 6;
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
        expect.stringContaining("Question 7")
      );

      let numberBox: HTMLElement;

      expect(() => {
        numberBox = screen.getByRole("textbox");
      }).not.toThrow();
    });

    it('can have an integer entered', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const numberBox = screen.getByRole("textbox");
      const nextButton = screen.getByText("Next");
      const prevButton = screen.getByText("Previous");

      expect(numberBox.value).toEqual("");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);

      fireEvent.change(numberBox, { target: { value: 3 } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(numberBox.value).toEqual("3");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);
    });

    it('cannot have a non-numeric character entered', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const numberBox = screen.getByRole("textbox");
      const nextButton = screen.getByText("Next");
      const prevButton = screen.getByText("Previous");

      expect(numberBox.value).toEqual("3");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);

      fireEvent.change(numberBox, { target: { value: 'a' } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(numberBox.value).toEqual("a");
      // If the answer is not valid, the Next and Previous buttons are disabled
      expect(nextButton.disabled).toEqual(true);
      expect(prevButton.disabled).toEqual(true);

      fireEvent.change(numberBox, { target: { value: 3 } });
    });

    it('cannot have a floating-point number entered', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const numberBox = screen.getByRole("textbox");
      const nextButton = screen.getByText("Next");
      const prevButton = screen.getByText("Previous");

      expect(numberBox.value).toEqual("3");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);

      fireEvent.change(numberBox, { target: { value: 3.5 } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(numberBox.value).toEqual("3.5");
      // If the answer is not valid, the Next and Previous buttons are disabled
      expect(nextButton.disabled).toEqual(true);
      expect(prevButton.disabled).toEqual(true);

      fireEvent.change(numberBox, { target: { value: 3 } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(numberBox.value).toEqual("3");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);
    });
  });

  describe('Datatype tests: integer slider', () => {
    it('displays a slider widget in Question 8', () => {
      testStore.getState().stage = 7;
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
        expect.stringContaining("Question 8")
      );

      let slideWidget: HTMLElement;

      expect(() => {
        slideWidget = screen.getByRole("slider");
      }).not.toThrow();

      expect(screen.getByText("The worst", {exact: false}).innerHTML).toEqual(
        expect.stringContaining("1")
      );
      expect(screen.getByText("The best", {exact: false}).innerHTML).toEqual(
        expect.stringContaining("10")
      );
    });

    it('updates the value in the box when the slider is changed', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const slideWidget = screen.getByRole("slider").parentElement; // Entire slider widget
      const slideHandle = screen.getByRole("slider"); // Slider handle
      const textBox = screen.getByText("On a scale of 1 to 10:");

      expect(slideHandle.getAttribute("aria-valuenow")).toEqual(null);
      expect(textBox.children[1].innerHTML).toEqual("");

      // Mocking the slider dimensions
      slideWidget.getBoundingClientRect = jest.fn(() => {
        return {
          bottom: 300,
          height: 100,
          left: 10,
          right: 20,
          top: 200,
          width: 10,
          x: 50,
          y: 250,
          toJSON: null
        };
      });

      fireEvent.mouseDown(slideWidget, {clientX: 55, clientY: 230});

      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(slideHandle.getAttribute("aria-valuenow")).toEqual("7");
      expect(textBox.children[1].innerHTML).toEqual("7");
    });
  });

  describe('Datatype tests: float', () => {
    it('displays a textbox in Question 9', () => {
      testStore.getState().stage = 8;
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
        expect.stringContaining("Question 9")
      );

      let floatBox: HTMLElement;

      expect(() => {
        floatBox = screen.getByRole("textbox");
      }).not.toThrow();
    });

    it('can have an integer entered', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const floatBox = screen.getByRole("textbox");
      const nextButton = screen.getByText("Next");
      const prevButton = screen.getByText("Previous");

      expect(floatBox.value).toEqual("");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);

      fireEvent.change(floatBox, { target: { value: 3 } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(floatBox.value).toEqual("3");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);
    });

    it('can have a floating-point number entered', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const floatBox = screen.getByRole("textbox");
      const nextButton = screen.getByText("Next");
      const prevButton = screen.getByText("Previous");

      expect(floatBox.value).toEqual("3");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);

      fireEvent.change(floatBox, { target: { value: 3.5 } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(floatBox.value).toEqual("3.5");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);
    });

    it('cannot have a non-numeric character entered', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const floatBox = screen.getByRole("textbox");
      const nextButton = screen.getByText("Next");
      const prevButton = screen.getByText("Previous");

      expect(floatBox.value).toEqual("3.5");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);

      fireEvent.change(floatBox, { target: { value: 'a' } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(floatBox.value).toEqual("a");
      // If the answer is not valid, the Next and Previous buttons are disabled
      expect(nextButton.disabled).toEqual(true);
      expect(prevButton.disabled).toEqual(true);

      fireEvent.change(floatBox, { target: { value: 3.5 } });
    });
  });

  describe('Datatype tests: text', () => {
    it('displays a textbox in Question 2', () => {
      testStore.getState().stage = 1;
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
        expect.stringContaining("Question 2")
      );

      let answerBox: HTMLElement;

      expect(() => {
        answerBox = screen.getByRole("textbox");
      }).not.toThrow();
    });

    it('can have any text entered', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const answerBox = screen.getByRole("textbox");
      const nextButton = screen.getByText("Next");
      const prevButton = screen.getByText("Previous");

      expect(answerBox.value).toEqual("");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);

      fireEvent.change(answerBox, { target: { value: 'a' } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(answerBox.value).toEqual("a");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);

      fireEvent.change(answerBox, { target: { value: 23 } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(answerBox.value).toEqual("23");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);

      fireEvent.change(answerBox, { target: { value: 'here\'s a longer sentence' } });
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(answerBox.value).toEqual("here's a longer sentence");
      expect(nextButton.disabled).toEqual(false);
      expect(prevButton.disabled).toEqual(false);
    });
  });

  describe('Datatype tests: date', () => {
    // Date will need more testing, as it's not used in any existing surveys
    it('displays a date box in Question 10', () => {
      testStore.getState().stage = 9;
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
        expect.stringContaining("Question 10")
      );

      let dateBox: HTMLElement;

      expect(() => {
        // dateBox = screen.getByRole("datetime");
        dateBox = screen.getByDisplayValue("");
      }).not.toThrow();
      expect(dateBox.type).toEqual("date");
    });
    it.todo('can have a date input in the YYYY-MM-DD format');
    it.todo('cannot have a date input in other formats');
    it.todo('cannot have a regular number input');
    it.todo('cannot have a non-numeric character (besides "-") entered');
  });

  describe('Datatype tests: range', () => {
    it('displays 3 unchecked radio select buttons in Question 12', () => {
      testStore.getState().stage = 11;
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
        expect.stringContaining("Question 12")
      );

      let radioButtons: HTMLElement[];

      expect(() => {
        radioButtons = screen.getAllByRole("radio");
      }).not.toThrow();
      expect(radioButtons.length).toEqual(3);
      radioButtons.forEach((rButton) => {
          expect(rButton.type).toEqual("radio");
          expect(rButton.checked).toEqual(false);
      });
    });

    it('selects a radio button when it is clicked', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const answer1Select = screen.getByLabelText("First answer");
      
      expect(answer1Select.checked).toEqual(false);

      fireEvent.click(answer1Select);
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(answer1Select.checked).toEqual(true);
    });

    it('de-selects a checked radio button when another is clicked', () => {
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      const answer1Select = screen.getByLabelText("First answer");
      const answer2Select = screen.getByLabelText("Second answer");
      
      expect(answer1Select.checked).toEqual(true);
      expect(answer2Select.checked).toEqual(false);

      fireEvent.click(answer2Select);
      rerender(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(answer1Select.checked).toEqual(false);
      expect(answer2Select.checked).toEqual(true);
    });
  });

  describe('Datatype tests: multiselect', () => {
    it('displays multiselect options in Question 4', () => {
      testStore.getState().stage = 3;
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
        expect.stringContaining("Question 4")
      );

      let checkboxes: HTMLElement[];

      expect(() => {
        checkboxes = screen.getAllByRole("checkbox");
      }).not.toThrow();

      checkboxes.forEach((cBox) => {
          expect(cBox.type).toEqual("checkbox");
      });
    });
  });

  describe('Datatype tests: consent', () => {
    it('displays one checkbox and consent text in Question 11', () => {
      testStore.getState().stage = 10;
      const { rerender, asFragment } = render(
        <Provider store={testStore}>
          <App />
        </Provider>
      );

      expect(screen.getByText("title", { exact: false }).innerHTML).toEqual(
        expect.stringContaining("Question 11")
      );

      let checkBox: HTMLElement;

      expect(() => {
        checkBox = screen.getByRole("checkbox");
      }).not.toThrow();
      expect(screen.getByText("consent", { exact: false }).innerHTML).toEqual(
        expect.stringContaining("CIC Cancer")
      );
    });
  });
});

// Checking the Redux store directly
describe('Reducer tests: the state', () => {
  const testStore = createStore(
    actions.promsPageReducer,
    composeEnhancers(applyMiddleware(thunk))
  );

  describe('Basic tests', () => {
    /*
    * Test 1
    */
    it('can go to the next question from the first question', () => {
      expect(testStore.getState().stage).toEqual(0);
      testStore.dispatch(actions.goNext());
      expect(testStore.getState().stage).toEqual(1);
    });

    /*
    * Test 2
    */
    it('can go to the previous question from the second question', () => {
      expect(testStore.getState().stage).toEqual(1);
      testStore.dispatch(actions.goPrevious());
      expect(testStore.getState().stage).toEqual(0);
    });
  });

  describe("Preconditional tests: 'or'", () => {
    /*
    * Test 3
    */
    it('only has three questions', () => {
      expect(testStore.getState().questions.length).toEqual(3);
    });

    /*
    * Test 4
    */
    it('can have data entered', () => {
      expect(testStore.getState().answers).toStrictEqual({});
      // console.log(testStore.getState().answers);
      testStore.dispatch(actions.enterData({cde: "registryQ1", value: "answer1", isValid: true}));
      expect(testStore.getState().answers).not.toEqual({});
      // console.log(testStore.getState());
    });

    /*
    * Test 5
    */
    it('has the third question (preconditional) available after entering data in the first question', () => {
      expect(testStore.getState().questions.length).toEqual(4);
    });

    /*
    * Test 6
    */
    it('has the third question remain available after changing data in the first question', () => {
      expect(testStore.getState().questions[2].cde).toEqual("registryQ3");
      expect(testStore.getState().answers).toHaveProperty("registryQ1");
      expect(testStore.getState().answers[regQ1String]).toEqual("answer1");
      expect(testStore.getState().questions.length).toEqual(4);
      testStore.dispatch(actions.enterData({cde: "registryQ1", value: "answer2", isValid: true}));
      expect(testStore.getState().questions[2].cde).toEqual("registryQ3");
      expect(testStore.getState().answers).toHaveProperty("registryQ1");
      expect(testStore.getState().answers[regQ1String]).not.toEqual("answer1");
      expect(testStore.getState().questions.length).toEqual(4);
    });
  });

  describe("Preconditional tests: '='", () => {
    /*
    * Test 7
    */
    it('does not make the fourth question available if "Good" is answered in the third question', () => {
      expect(testStore.getState().questions.length).toEqual(4);
      expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
      testStore.dispatch(actions.enterData({cde: "registryQ3", value: "good_answer", isValid: true}));
      expect(testStore.getState().questions.length).toEqual(4);
      expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
    });

    /*
    * Test 8
    */
    it('does not make the fourth question available if "Not so good" is answered in the third question', () => {
      expect(testStore.getState().questions.length).toEqual(4);
      expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
      testStore.dispatch(actions.enterData({cde: "registryQ3", value: "not_good_answer", isValid: true}));
      expect(testStore.getState().questions.length).toEqual(4);
      expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
    });

    /*
    * Test 9
    */
    it('makes the fourth question available if "Bad" is answered in the third question', () => {
      expect(testStore.getState().questions.length).toEqual(4);
      expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
      testStore.dispatch(actions.enterData({cde: "registryQ3", value: "bad_answer", isValid: true}));
      expect(testStore.getState().questions.length).toEqual(5);
      expect(testStore.getState().questions[3].cde).toEqual("registryQ4");
    });
  });

  describe("Preconditional tests: 'contains'", () => {
    /*
    * Test 10
    */
    it('does not make the fifth question available if "Work is stressful" is selected in the fourth question', () => {
      expect(testStore.getState().questions.length).toEqual(5);
      expect(testStore.getState().questions[4].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ4String]).toBeUndefined();
      testStore.dispatch(actions.enterData({cde: "registryQ4", value: ["work_answer"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(5);
      expect(testStore.getState().questions[4].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ4String]).toEqual(["work_answer"]);
    });

    /*
    * Test 11
    */
    it('does not make the fifth question available if "Work is stressful" and "Can\'t see my friends" are selected in the fourth question', () => {
      expect(testStore.getState().questions.length).toEqual(5);
      expect(testStore.getState().questions[4].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ4String]).toEqual(["work_answer"]);
      testStore.dispatch(actions.enterData({cde: "registryQ4", value: ["work_answer", "friends_answer"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(5);
      expect(testStore.getState().questions[4].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ4String]).toEqual(["work_answer", "friends_answer"]);
    });

    /*
    * Test 12
    */
    it('does not make the fifth question available if "Can\'t see my friends" and "Just a bad day" are selected in the fourth question', () => {
      expect(testStore.getState().questions.length).toEqual(5);
      expect(testStore.getState().questions[4].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ4String]).toEqual(["work_answer", "friends_answer"]);
      testStore.dispatch(actions.enterData({cde: "registryQ4", value: ["friends_answer", "day_answer"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(5);
      expect(testStore.getState().questions[4].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ4String]).toEqual(["friends_answer", "day_answer"]);
    });

    /*
    * Test 13
    */
    it('makes the fifth question available if "React is difficult" is selected in the fourth question with any other answers', () => {
      expect(testStore.getState().questions.length).toEqual(5);
      expect(testStore.getState().questions[4].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ4String]).toEqual(["friends_answer", "day_answer"]);
      testStore.dispatch(actions.enterData({cde: "registryQ4", value: ["react_answer"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[4].cde).toEqual("registryQ5");
      expect(testStore.getState().answers[regQ4String]).toEqual(["react_answer"]);
      testStore.dispatch(actions.enterData({cde: "registryQ4", value: ["react_answer", "day_answer"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[4].cde).toEqual("registryQ5");
      expect(testStore.getState().answers[regQ4String]).toEqual(["react_answer", "day_answer"]);
      testStore.dispatch(actions.enterData({cde: "registryQ4", value: ["react_answer", "day_answer", "work_answer", "friends_answer"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[4].cde).toEqual("registryQ5");
      expect(testStore.getState().answers[regQ4String]).toEqual(["react_answer", "day_answer", "work_answer", "friends_answer"]);
    });
  });

  describe("Preconditional tests: 'intersection'", () => {
    it('does not make the sixth question available if "It\'s hard to read" is selected in the fifth question', () => {
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[5].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ5String]).toBeUndefined();
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["hard_to_read"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[5].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ5String]).toEqual(["hard_to_read"]);
    });

    it('does not make the sixth question available if "It\'s hard to read" and "I don\'t understand it" are selected in the fifth question', () => {
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[5].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ5String]).toEqual(["hard_to_read"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["hard_to_read", "zero_understanding"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[5].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ5String]).toEqual(["hard_to_read", "zero_understanding"]);
    });

    it('makes the sixth question available if "It has too many dependencies" is selected with any other answer in the fifth question', () => {
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[5].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ5String]).toEqual(["hard_to_read", "zero_understanding"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["too_many_deps"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(7);
      expect(testStore.getState().questions[5].cde).toEqual("registryQ6");
      expect(testStore.getState().answers[regQ5String]).toEqual(["too_many_deps"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["too_many_deps", "hard_to_read"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(7);
      expect(testStore.getState().questions[5].cde).toEqual("registryQ6");
      expect(testStore.getState().answers[regQ5String]).toEqual(["too_many_deps", "hard_to_read"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["too_many_deps", "hard_to_read", "zero_understanding"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(7);
      expect(testStore.getState().questions[5].cde).toEqual("registryQ6");
      expect(testStore.getState().answers[regQ5String]).toEqual(["too_many_deps", "hard_to_read", "zero_understanding"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["hard_to_read", "zero_understanding"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[5].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ5String]).toEqual(["hard_to_read", "zero_understanding"]);
    });

    it('makes the sixth question available if "It\'s made by Facebook" is selected with any other answer in the fifth question', () => {
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[5].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ5String]).toEqual(["hard_to_read", "zero_understanding"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["by_fb"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(7);
      expect(testStore.getState().questions[5].cde).toEqual("registryQ6");
      expect(testStore.getState().answers[regQ5String]).toEqual(["by_fb"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["by_fb", "hard_to_read"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(7);
      expect(testStore.getState().questions[5].cde).toEqual("registryQ6");
      expect(testStore.getState().answers[regQ5String]).toEqual(["by_fb", "hard_to_read"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["by_fb", "hard_to_read", "zero_understanding"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(7);
      expect(testStore.getState().questions[5].cde).toEqual("registryQ6");
      expect(testStore.getState().answers[regQ5String]).toEqual(["by_fb", "hard_to_read", "zero_understanding"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["hard_to_read", "zero_understanding"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[5].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ5String]).toEqual(["hard_to_read", "zero_understanding"]);
    });

    it('makes the sixth question available if "It has too many dependencies" and "It\'s made by Facebook" are selected in the fifth question', () => {
      expect(testStore.getState().questions.length).toEqual(6);
      expect(testStore.getState().questions[5].cde).toEqual("PROMSConsent");
      expect(testStore.getState().answers[regQ5String]).toEqual(["hard_to_read", "zero_understanding"]);
      testStore.dispatch(actions.enterData({cde: regQ5String, value: ["too_many_deps", "by_fb"], isValid: true}));
      expect(testStore.getState().questions.length).toEqual(7);
      expect(testStore.getState().questions[5].cde).toEqual("registryQ6");
      expect(testStore.getState().answers[regQ5String]).toEqual(["too_many_deps", "by_fb"]);
    });
  });
});

// Testing actions by adding middleware to regular stores capture them
describe('Action tests: the app', () => {
  const testStore = createStore(
    actions.promsPageReducer,
    composeEnhancers(applyMiddleware(thunk, captureAction))
  );

  beforeEach(() => {
    actionList = [];
  });

  beforeAll(() => {
    moxios.install();
  });

  afterAll(() => {
    moxios.uninstall();
  });

  it('fires the goNext action when the "Next" button is clicked', () => {
    const expectedActions = [
      {
        "type": "PROMS_NEXT"
      }
    ];

    // Mock render and interact
    const { rerender, asFragment } = render(
      <Provider store={testStore}>
        <App />
      </Provider>
    );

    const nextButton = screen.getByText("Next");
    fireEvent.click(nextButton);

    expect(actionList).toEqual(expectedActions);
  });

  it('fires the goPrevious action when the "Previous" button is clicked', () => {
    const expectedActions = [
      {
        "type": "PROMS_PREVIOUS"
      }
    ];

    // Mock render and interact
    const { rerender, asFragment } = render(
      <Provider store={testStore}>
        <App />
      </Provider>
    );

    const prevButton = screen.getByText("Previous");
    fireEvent.click(prevButton);

    expect(actionList).toEqual(expectedActions);
  });

  it('fires the enterData action when a radio button is clicked', () => {
    const expectedActions = [
      {
        "payload": {
          "cde": "registryQ1",
          "value": "answer1",
          "isValid": true
        },
        "type": "PROMS_ENTER_DATA"
      },
      {
        "payload": {
          "cde": "registryQ1",
          "value": "answer2",
          "isValid": true
        },
        "type": "PROMS_ENTER_DATA"
      }
    ];

    // Mock render and interact
    const { rerender, asFragment } = render(
      <Provider store={testStore}>
        <App />
      </Provider>
    );

    const answer1Select = screen.getByLabelText("Answer 1", { exact: false });
    const answer2Select = screen.getByLabelText("Answer 2", { exact: false });
    fireEvent.click(answer1Select);
    fireEvent.click(answer2Select);

    expect(actionList).toEqual(expectedActions);

    // Need to add in answer to display preconditional questions
    testStore.dispatch(actions.enterData({cde: "registryQ3", value: "bad_answer", isValid: true}));
  });

  it('fires the enterData action when a checkbox is clicked', () => {
    testStore.getState().stage = 3;

    const expectedActions = [
      {
        "payload": {
          "cde": "registryQ4",
          "value": ["work_answer"],
          "isValid": true
        },
        "type": "PROMS_ENTER_DATA"
      },
      {
        "payload": {
          "cde": "registryQ4",
          "value": ["work_answer", "react_answer"],
          "isValid": true
        },
        "type": "PROMS_ENTER_DATA"
      }
    ];

    // Mock render and interact
    const { rerender, asFragment } = render(
      <Provider store={testStore}>
        <App />
      </Provider>
    );

    const answer1Select = screen.getByLabelText("Work is stressful", { exact: false });
    const answer2Select = screen.getByLabelText("React is difficult", { exact: false });
    fireEvent.click(answer1Select);
    rerender(
      <Provider store={testStore}>
        <App />
      </Provider>
    );
    fireEvent.click(answer2Select);

    expect(actionList).toEqual(expectedActions);
  });

  it('fires the enterData action when text is entered to a text field', () => {
    testStore.getState().stage = 1;

    const expectedActions = [
      {
        "payload": {
          "cde": "registryQ2",
          "value": "blah",
          "isValid": true
        },
        "type": "PROMS_ENTER_DATA"
      },
      {
        "payload": {
          "cde": "registryQ2",
          "value": "Hello world",
          "isValid": true
        },
        "type": "PROMS_ENTER_DATA"
      },
      {
        "payload": {
          "cde": "registryQ2",
          "value": "12345",
          "isValid": true
        },
        "type": "PROMS_ENTER_DATA"
      }
    ];

    // Mock render and interact
    const { rerender, asFragment } = render(
      <Provider store={testStore}>
        <App />
      </Provider>
    );

    const answerBox = screen.getByRole("textbox");
    fireEvent.change(answerBox, { target: { value: 'blah' } });
    fireEvent.change(answerBox, { target: { value: 'Hello world' } });
    fireEvent.change(answerBox, { target: { value: 12345 } });

    expect(actionList).toEqual(expectedActions);
  });

/* Another test with problems - the payload contains what appears to be an Event, but has
 * nothing defined. Additionally, it's not clear where this event comes from.
 ****************************************************************************************/
  it('fires the submitAnswers action when the "Submit" button is clicked on the last page', (done) => {
    const numStages = testStore.getState().questions.length;
    testStore.getState().stage = numStages - 1

    const expectedActions = [
      {
        "type": "PROMS_SUBMIT"
      }
    ];

    // Mock render and interact
    const { rerender, asFragment } = render(
      <Provider store={testStore}>
        <App />
      </Provider>
    );

    const submitButton = screen.getByText("Submit Answers");
    fireEvent.click(submitButton);
    moxios.wait(() => {
      expect(actionList[0].type).toEqual(expectedActions[0].type);
      done();
    });
  });
});