/// <reference types="cypress" />

import { gql } from "@apollo/client";
import { MockedProvider } from "@apollo/client/testing";
import React from "react";
import { Route, Routes } from "react-router-dom";
import {
  graphqlQueriesMocksData,
  graphqlQueriesMocksQuery,
} from "../../../mocks/data/graphqlQueries";
import { schemaMocks } from "../../../mocks/data/schema";
import { TestProvider } from "../../../mocks/jotai/atom";
import ObjectItems from "../../../src/screens/object-items/object-items-paginated";
import { schemaState } from "../../../src/state/atoms/schema.atom";

// URL for the current view
const graphqlQueryItemsUrl = "/objects/graphql_query";

// Path that will match the route to display the component
const graphqlQueryItemsPath = "/objects/:objectname";

// Mock the apollo query and data
const mocks: any[] = [
  {
    request: {
      query: gql`
        ${graphqlQueriesMocksQuery}
      `,
    },
    result: {
      data: graphqlQueriesMocksData,
    },
  },
];

// Provide the initial value for jotai
const ObjectItemsProvider = () => {
  return (
    <TestProvider initialValues={[[schemaState, schemaMocks]]}>
      <ObjectItems />
    </TestProvider>
  );
};

describe("List screen", () => {
  it("should fetch items and render list", () => {
    cy.viewport(1920, 1080);

    // Mount the view with the default route and the mocked data
    cy.mount(
      <MockedProvider mocks={mocks} addTypename={false}>
        <Routes>
          <Route element={<ObjectItemsProvider />} path={graphqlQueryItemsPath} />
        </Routes>
      </MockedProvider>,
      {
        // Add iniital route for the app router, to display the current items view
        routerProps: {
          initialEntries: [graphqlQueryItemsUrl],
        },
      }
    );

    // Should check that the last item in pagination is page number 100
    cy.get(":nth-child(7) > .cursor-pointer").should("have.text", "100");

    // Should display the last item for the current page
    cy.get(":nth-child(10) > :nth-child(1)").should("exist");

    // Should display a tag in the tags list for the 4th item in the list
    cy.get(":nth-child(4) > :nth-child(5) > div.flex > :nth-child(3)").should(
      "have.text",
      "maroon"
    );
  });
});