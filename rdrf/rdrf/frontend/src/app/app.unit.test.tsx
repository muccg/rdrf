import * as React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { applyMiddleware, compose, createStore } from "redux";
import thunk from "redux-thunk";
import * as actions from "../pages/proms_page/reducers";
import App from "./index";

const devtoolsExtension = "__REDUX_DEVTOOLS_EXTENSION_COMPOSE__";
const composeEnhancers = window[devtoolsExtension] || compose;

const testStore = createStore(
  actions.promsPageReducer,
  composeEnhancers(applyMiddleware(thunk))
);

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

describe("A test App using Redux", () => {
  it("can render", () => {
    const { rerender, asFragment } = render(
      <Provider store={testStore}>
        <App />
      </Provider>
    );
  });
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
                          Anwser 1
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
  it('can got to the next question from the first question (non-render)', () => {
    expect(testStore.getState().stage).toEqual(0);
    testStore.dispatch(actions.goNext());
    expect(testStore.getState().stage).toEqual(1);
  });
  it('can got to the previous question from the second question (non-render)', () => {
    expect(testStore.getState().stage).toEqual(1);
    testStore.dispatch(actions.goPrevious());
    expect(testStore.getState().stage).toEqual(0);
  });
  it('can have data entered (non-render)', () => {
    expect(testStore.getState().answers).toStrictEqual({});
    // console.log(testStore.getState().answers);
    testStore.dispatch(actions.enterData({cde: "registryQ1", value: "answer1", isValid: true}));
    expect(testStore.getState().answers).not.toEqual({});
    // console.log(testStore.getState());
  });
});
