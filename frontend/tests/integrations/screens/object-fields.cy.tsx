/// <reference types="cypress" />

import { MockedProvider } from "@apollo/client/testing";
import React from "react";
import { Route, Routes } from "react-router-dom";
import { withAuth } from "../../../src/decorators/withAuth";
import { schemaState } from "../../../src/state/atoms/schema.atom";

import { gql } from "@apollo/client";
import { ACCESS_TOKEN_KEY } from "../../../src/config/constants";
import ObjectItems from "../../../src/screens/object-items/object-items-paginated";
import { encodeJwt } from "../../../src/utils/common";
import { accountDetailsMocksSchema } from "../../mocks/data/account";
import {
  profileDetailsMocksData,
  profileDetailsMocksQuery,
  profileId,
} from "../../mocks/data/profile";
import {
  taskMocksData as taskMocksData1,
  taskMocksQuery as taskMocksQuery1,
  taskMocksSchema as taskMocksSchema1,
  taskMocksSchemaOptional as taskMocksSchemaOptionnal1,
} from "../../mocks/data/task_1";
import {
  taskMocksData as taskMocksData2,
  taskMocksQuery as taskMocksQuery2,
  taskMocksSchema as taskMocksSchema2,
  taskMocksSchemaOptional as taskMocksSchemaOptional2,
  taskMocksSchemaWithDefaultValue as taskMocksSchemaWithDefaultValue2,
} from "../../mocks/data/task_2";
import { TestProvider } from "../../mocks/jotai/atom";

// URL for the current view
const mockedUrl = "/objects/Task";

// Path that will match the route to display the component
const mockedPath = "/objects/:objectname";

// Mock the apollo query and data
const mocks: any[] = [
  {
    request: {
      query: gql`
        ${profileDetailsMocksQuery}
      `,
    },
    result: {
      data: profileDetailsMocksData,
    },
  },
  {
    request: {
      query: gql`
        ${taskMocksQuery1}
      `,
    },
    result: {
      data: taskMocksData1,
    },
  },
  {
    request: {
      query: gql`
        ${taskMocksQuery2}
      `,
    },
    result: {
      data: taskMocksData2,
    },
  },
];

const AuthenticatedObjectItems = withAuth(ObjectItems);

describe("Object list", () => {
  beforeEach(function () {
    const data = {
      sub: profileId,
      user_claims: {
        role: "admin",
      },
    };

    const token = encodeJwt(data);

    sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
  });

  it("should open the add panel, submit without filling the text field and display a required message", function () {
    cy.viewport(1920, 1080);

    cy.intercept("POST", "/graphql/main ", this.mutation).as("mutate");

    // Provide the initial value for jotai
    const ObjectItemsProvider = () => {
      return (
        <TestProvider
          initialValues={[[schemaState, [...accountDetailsMocksSchema, ...taskMocksSchema1]]]}>
          <AuthenticatedObjectItems />
        </TestProvider>
      );
    };

    // Mount the view with the default route and the mocked data
    cy.mount(
      <MockedProvider mocks={mocks} addTypename={false}>
        <Routes>
          <Route element={<ObjectItemsProvider />} path={mockedPath} />
        </Routes>
      </MockedProvider>,
      {
        // Add iniital route for the app router, to display the current items view
        routerProps: {
          initialEntries: [mockedUrl],
        },
      }
    );

    // Open edit panel
    cy.get(".p-2").click();

    // Save
    cy.contains("Save").click();

    // The required message should appear
    cy.get(".sm\\:col-span-7 > .relative > .absolute").should("have.text", "Required");
  });

  it("should open the add panel, submit after filling the text field and do not display a required message", function () {
    cy.viewport(1920, 1080);

    cy.intercept("POST", "/graphql/main ", this.mutation).as("mutate");

    // Provide the initial value for jotai
    const ObjectItemsProvider = () => {
      return (
        <TestProvider
          initialValues={[
            [schemaState, [...accountDetailsMocksSchema, ...taskMocksSchemaOptionnal1]],
          ]}>
          <AuthenticatedObjectItems />
        </TestProvider>
      );
    };

    // Mount the view with the default route and the mocked data
    cy.mount(
      <MockedProvider mocks={mocks} addTypename={false}>
        <Routes>
          <Route element={<ObjectItemsProvider />} path={mockedPath} />
        </Routes>
      </MockedProvider>,
      {
        // Add iniital route for the app router, to display the current items view
        routerProps: {
          initialEntries: [mockedUrl],
        },
      }
    );

    // Open edit panel
    cy.get(".p-2").click();

    // Save
    cy.contains("Save").click();

    // The required message should appear
    cy.get(".sm\\:col-span-7 > .relative > .absolute").should("not.exist");
  });

  it("should open the add panel, submit without checking the checkbox and display a required message", function () {
    cy.viewport(1920, 1080);

    cy.intercept("POST", "/graphql/main ", this.mutation).as("mutate");

    // Provide the initial value for jotai
    const ObjectItemsProvider = () => {
      return (
        <TestProvider
          initialValues={[[schemaState, [...accountDetailsMocksSchema, ...taskMocksSchema2]]]}>
          <AuthenticatedObjectItems />
        </TestProvider>
      );
    };

    // Mount the view with the default route and the mocked data
    cy.mount(
      <MockedProvider mocks={mocks} addTypename={false}>
        <Routes>
          <Route element={<ObjectItemsProvider />} path={mockedPath} />
        </Routes>
      </MockedProvider>,
      {
        // Add iniital route for the app router, to display the current items view
        routerProps: {
          initialEntries: [mockedUrl],
        },
      }
    );

    // Open edit panel
    cy.get(".p-2").click();

    // Save
    cy.contains("Save").click();

    // The required message should appear
    cy.get(".flex-col > .relative > .absolute").should("have.text", "Required");
  });

  it("should open the add panel, submit without checking the checkbox and should not display a required message (default value is defined)", function () {
    cy.viewport(1920, 1080);

    cy.intercept("POST", "/graphql/main ", this.mutation).as("mutate");

    // Provide the initial value for jotai
    const ObjectItemsProvider = () => {
      return (
        <TestProvider
          initialValues={[
            [schemaState, [...accountDetailsMocksSchema, ...taskMocksSchemaWithDefaultValue2]],
          ]}>
          <AuthenticatedObjectItems />
        </TestProvider>
      );
    };

    // Mount the view with the default route and the mocked data
    cy.mount(
      <MockedProvider mocks={mocks} addTypename={false}>
        <Routes>
          <Route element={<ObjectItemsProvider />} path={mockedPath} />
        </Routes>
      </MockedProvider>,
      {
        // Add iniital route for the app router, to display the current items view
        routerProps: {
          initialEntries: [mockedUrl],
        },
      }
    );

    // Open edit panel
    cy.get(".p-2").click();

    // Save
    cy.contains("Save").click();

    // The required message should appear
    cy.get(".flex-col > .relative > .absolute").should("not.exist");
  });

  it("should open the add panel, submit without checking the checkbox and should not display a required message (optional))", function () {
    cy.viewport(1920, 1080);

    cy.intercept("POST", "/graphql/main ", this.mutation).as("mutate");

    // Provide the initial value for jotai
    const ObjectItemsProvider = () => {
      return (
        <TestProvider
          initialValues={[
            [schemaState, [...accountDetailsMocksSchema, ...taskMocksSchemaOptional2]],
          ]}>
          <AuthenticatedObjectItems />
        </TestProvider>
      );
    };

    // Mount the view with the default route and the mocked data
    cy.mount(
      <MockedProvider mocks={mocks} addTypename={false}>
        <Routes>
          <Route element={<ObjectItemsProvider />} path={mockedPath} />
        </Routes>
      </MockedProvider>,
      {
        // Add iniital route for the app router, to display the current items view
        routerProps: {
          initialEntries: [mockedUrl],
        },
      }
    );

    // Open edit panel
    cy.get(".p-2").click();

    // Save
    cy.contains("Save").click();

    // The required message should appear
    cy.get(".flex-col > .relative > .absolute").should("not.exist");
  });
});