import React from "react";
import { BADGE_TYPES, Badge } from "../../../src/components/badge";

declare const cy: any;

describe("Badge component", () => {
  it("should render VALIDATE badge correctly", () => {
    cy.mount(<Badge type={BADGE_TYPES.VALIDATE}>{"Validate"}</Badge>);
  });

  it("should render WARNING badge correctly", () => {
    cy.mount(<Badge type={BADGE_TYPES.WARNING}>{"Warning"}</Badge>);
  });

  it("should render CANCEL badge correctly", () => {
    cy.mount(<Badge type={BADGE_TYPES.CANCEL}>{"Cancel"}</Badge>);
  });

  it("should render DEFAULT badge correctly", () => {
    cy.mount(<Badge>{"Default"}</Badge>);
  });
});
