import * as React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { applyMiddleware, compose, createStore } from "redux";
import thunk from "redux-thunk";
import * as actions from "../pages/proms_page/reducers";
import App from "./index";

const devtoolsExtension = "__REDUX_DEVTOOLS_EXTENSION_COMPOSE__";
const composeEnhancers = window[devtoolsExtension] || compose;

/*
const unsubscribe = testStore.subscribe(() =>
  global.console.log(testStore.getState())
);
*/

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
    composeEnhancers(applyMiddleware(thunk))
  );

  /*
  * Test 1
  */
  it("can render", () => {
    const { rerender, asFragment } = render(
      <Provider store={testStore}>
        <App />
      </Provider>
    );
  });

  /*
  * Test 2
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
  });

  /*
  * Test 3
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

    testStore.dispatch(actions.goNext());

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
  * Test 4
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

    var answer1Select = screen.getByLabelText("Answer 1", { exact: false });
    var answer2Select = screen.getByLabelText("Answer 2", { exact: false });
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
    expect(testStore.getState().answers["registryQ1"]).not.toEqual("answer1");

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
    var goodAnswerSelect = screen.getByLabelText("Good");
    var notGoodSelect = screen.getByLabelText("Not so good");
    var badAnswerSelect = screen.getByLabelText("Bad");

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
    var goodAnswerSelect = screen.getByLabelText("Good");
    var notGoodSelect = screen.getByLabelText("Not so good");
    var badAnswerSelect = screen.getByLabelText("Bad");

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
    var goodAnswerSelect = screen.getByLabelText("Good");
    var notGoodSelect = screen.getByLabelText("Not so good");
    var badAnswerSelect = screen.getByLabelText("Bad");

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
    var goodAnswerSelect = screen.getByLabelText("Good");
    var notGoodSelect = screen.getByLabelText("Not so good");
    var badAnswerSelect = screen.getByLabelText("Bad");

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
    var goodAnswerSelect = screen.getByLabelText("Good");
    var notGoodSelect = screen.getByLabelText("Not so good");
    var badAnswerSelect = screen.getByLabelText("Bad");

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
    var goodAnswerSelect = screen.getByLabelText("Good");
    var notGoodSelect = screen.getByLabelText("Not so good");
    var badAnswerSelect = screen.getByLabelText("Bad");

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

  /*
  * Tests to do
  */
  it.todo('does not make the fifth question available if "Work is stressful" is selected in the fourth question');
  it.todo('does not make the fifth question available if "Work is stressful" and "Can\'t see my friends" are selected in the fourth question');
  it.todo('does not make the fifth question available if "Can\'t see my friends" and "Just a bad day" are selected in the fourth question');
  it.todo('makes the fifth question available if "React is difficult" is selected in the fourth question with other answers');
});

// Checking the Redux store directly
describe('Reducer tests: the state', () => {
  const testStore = createStore(
    actions.promsPageReducer,
    composeEnhancers(applyMiddleware(thunk))
  );

  it('can go to the next question from the first question', () => {
    expect(testStore.getState().stage).toEqual(0);
    testStore.dispatch(actions.goNext());
    expect(testStore.getState().stage).toEqual(1);
  });

  it('can go to the previous question from the second question', () => {
    expect(testStore.getState().stage).toEqual(1);
    testStore.dispatch(actions.goPrevious());
    expect(testStore.getState().stage).toEqual(0);
  });

  it('only has three questions', () => {
    expect(testStore.getState().questions.length).toEqual(3);
  });

  it('can have data entered', () => {
    expect(testStore.getState().answers).toStrictEqual({});
    // console.log(testStore.getState().answers);
    testStore.dispatch(actions.enterData({cde: "registryQ1", value: "answer1", isValid: true}));
    expect(testStore.getState().answers).not.toEqual({});
    // console.log(testStore.getState());
  });

  it('has the third question (preconditional) available after entering data in the first question', () => {
    expect(testStore.getState().questions.length).toEqual(4);
  });

  it('has the third question remain available after changing data in the first question', () => {
    expect(testStore.getState().questions[2].cde).toEqual("registryQ3");
    expect(testStore.getState().answers).toHaveProperty("registryQ1");
    expect(testStore.getState().answers["registryQ1"]).toEqual("answer1");
    expect(testStore.getState().questions.length).toEqual(4);
    testStore.dispatch(actions.enterData({cde: "registryQ1", value: "answer2", isValid: true}));
    expect(testStore.getState().questions[2].cde).toEqual("registryQ3");
    expect(testStore.getState().answers).toHaveProperty("registryQ1");
    expect(testStore.getState().answers["registryQ1"]).not.toEqual("answer1");
    expect(testStore.getState().questions.length).toEqual(4);
  });

  it('does not make the fourth question available if "Good" is answered in the third question', () => {
    expect(testStore.getState().questions.length).toEqual(4);
    expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
    testStore.dispatch(actions.enterData({cde: "registryQ3", value: "good_answer", isValid: true}));
    expect(testStore.getState().questions.length).toEqual(4);
    expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
  });

  it('does not make the fourth question available if "Not so good" is answered in the third question', () => {
    expect(testStore.getState().questions.length).toEqual(4);
    expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
    testStore.dispatch(actions.enterData({cde: "registryQ3", value: "not_good_answer", isValid: true}));
    expect(testStore.getState().questions.length).toEqual(4);
    expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
  });

  it('makes the fourth question available if "Bad" is answered in the third question', () => {
    expect(testStore.getState().questions.length).toEqual(4);
    expect(testStore.getState().questions[3].cde).toEqual("PROMSConsent");
    testStore.dispatch(actions.enterData({cde: "registryQ3", value: "bad_answer", isValid: true}));
    expect(testStore.getState().questions.length).toEqual(5);
    expect(testStore.getState().questions[3].cde).toEqual("registryQ4");
  });
});
