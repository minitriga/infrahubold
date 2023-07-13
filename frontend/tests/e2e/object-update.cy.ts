/// <reference types="cypress" />

import { ADMIN_CREDENTIALS } from "../utils";

const ETHERNET_NAME = "Ethernet11";
const ETHERNET_NEW_NAME = "Ethernet117";
const ETHERNET_SPEED = 10000;
const ETHERNET_NEW_SPEED = "100";

describe("Object update", () => {
  beforeEach(function () {
    cy.login(ADMIN_CREDENTIALS.username, ADMIN_CREDENTIALS.password);

    cy.visit("/");
  });

  it("should update an object", function () {
    // Access the interfaces view
    cy.contains("Interface").click();

    // Access an interface
    cy.contains(ETHERNET_NAME).click();

    // The name should be the original one
    cy.get(":nth-child(3) > div.items-center > .mt-1").should("have.text", ETHERNET_NAME);

    // The speed should be the original one
    cy.get(":nth-child(5) > div.items-center > .mt-1").should("have.text", ETHERNET_SPEED);

    // Open the edit panel
    cy.contains("Edit").click();

    // The name should be correctly defined in the input
    cy.get(":nth-child(2) > .relative > .block").should("have.value", ETHERNET_NAME);
    cy.get(":nth-child(2) > .relative > .block").clear();
    cy.get(":nth-child(2) > .relative > .block").type(ETHERNET_NEW_NAME);

    // The name should be correctly defined in the input
    cy.get(":nth-child(4) > .relative > .block").should("have.value", ETHERNET_SPEED);
    cy.get(":nth-child(4) > .relative > .block").clear();
    cy.get(":nth-child(4) > .relative > .block").type(ETHERNET_NEW_SPEED);

    // Save
    cy.contains("Save").click();

    // Wait for the panel to be closed
    cy.get(".bg-gray-500").should("not.exist");

    // The name should be the original one
    cy.get(":nth-child(3) > div.items-center > .mt-1").should("have.text", ETHERNET_NEW_NAME);

    // The speed should be the original one
    cy.get(":nth-child(5) > div.items-center > .mt-1").should("have.text", ETHERNET_NEW_SPEED);
  });
});