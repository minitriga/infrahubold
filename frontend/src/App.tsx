import { useAtom } from "jotai";
import * as R from "ramda";
import { useCallback, useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { ToastContainer, toast, Slide } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { StringParam, useQueryParam } from "use-query-params";

import { graphQLClient } from "./graphql/graphqlClient";
import { ALERT_TYPES, Alert } from "./components/alert";
import { CONFIG } from "./config/config";
import { CUSTOM_COMPONENT_ROUTES, MAIN_ROUTES } from "./config/constants";
import SentryClient from "./config/sentry";
import { BRANCH_QUERY, iBranchData } from "./graphql/defined_queries/branch";
import Layout from "./screens/layout/layout";
import { branchState } from "./state/atoms/branch.atom";
import { branchesState } from "./state/atoms/branches.atom";
import { Config, configState } from "./state/atoms/config.atom";
import {
  genericSchemaState,
  genericsState,
  iGenericSchema,
  iGenericSchemaMapping,
  iNodeSchema,
  schemaState,
} from "./state/atoms/schema.atom";
import { schemaKindNameState } from "./state/atoms/schemaKindName.atom";
import "./styles/index.css";
import { fetchUrl } from "./utils/fetch";
import { QSP } from "./config/qsp";

const sortByOrderWeight = R.sortBy(R.compose(R.prop("order_weight")));

function App() {
  const [, setSchema] = useAtom(schemaState);
  const [, setGenerics] = useAtom(genericsState);
  const [, setGenericSchema] = useAtom(genericSchemaState);

  const [, setSchemaKindNameState] = useAtom(schemaKindNameState);
  const [branch] = useAtom(branchState);
  const [, setBranches] = useAtom(branchesState);
  const [config, setConfig] = useAtom(configState);
  const [branchInQueryString] = useQueryParam(QSP.BRANCH, StringParam);

  /**
   * Sentry configuration
   */
  SentryClient(config);

  /**
   * Fetch config from the backend and return it
   */
  const fetchConfig = async () => {
    try {
      return fetchUrl(CONFIG.CONFIG_URL);
    } catch (err) {
      toast(
        <Alert
          type={ALERT_TYPES.ERROR}
          message={"Something went wrong when fetching the config"}
        />
      );
      console.error("err: ", err);
      return undefined;
    }
  };

  /**
   * Set config in state atom
   */
  const setConfigInState = useCallback(async () => {
    const config: Config = await fetchConfig();
    setConfig(config);
  }, [setConfig]);

  useEffect(() => {
    setConfigInState();
  }, [setConfigInState]);

  /**
   * Fetch branches from the backend, sort, and return them
   */
  const fetchBranches = async () => {
    const sortByName = R.sortBy(R.compose(R.toLower, R.prop("name")));
    try {
      const data: iBranchData = await graphQLClient.request(BRANCH_QUERY);
      return sortByName(data.branch || []);
    } catch (err) {
      toast(
        <Alert
          type={ALERT_TYPES.ERROR}
          message={"Something went wrong when fetching the branch details"}
        />
      );
      console.error("err: ", err);
      return [];
    }
  };

  /**
   * Set branches in state atom
   */
  const setBranchesInState = useCallback(async () => {
    const branches = await fetchBranches();
    setBranches(branches);
  }, [setBranches]);

  useEffect(() => {
    setBranchesInState();
  }, [setBranchesInState]);

  /**
   * Fetch schema from the backend, sort, and return them
   */
  const fetchSchema = useCallback(async () => {
    const sortByName = R.sortBy(R.compose(R.toLower, R.prop("name")));
    try {
      const data = await fetchUrl(
        CONFIG.SCHEMA_URL(branchInQueryString ?? branch?.name)
      );

      return {
        schema: sortByName(data.nodes || []),
        generics: sortByName(data.generics || []),
      };
    } catch (err) {
      toast(
        <Alert
          type={ALERT_TYPES.ERROR}
          message={"Something went wrong when fetching the schema details"}
        />
      );
      console.error("err: ", err);
      return {
        schema: [],
        generics: [],
      };
    }
  }, [branch?.name, branchInQueryString]);

  /**
   * Set schema in state atom
   */
  const setSchemaInState = useCallback(async () => {
    const {
      schema,
      generics,
    }: { schema: iNodeSchema[]; generics: iGenericSchema[] } =
      await fetchSchema();
    schema.forEach((s) => {
      s.attributes = sortByOrderWeight(s.attributes || []);
      s.relationships = sortByOrderWeight(s.relationships || []);
    });
    setSchema(schema);
    setGenerics(generics);

    const schemaNames = R.map(R.prop("name"), schema);
    const schemaKinds = R.map(R.prop("kind"), schema);
    const schemaKindNameTuples = R.zip(schemaKinds, schemaNames);
    const schemaKindNameMap = R.fromPairs(schemaKindNameTuples);
    setSchemaKindNameState(schemaKindNameMap);

    const genericSchemaMapping: iGenericSchemaMapping = {};
    schema.forEach((schemaNode: any) => {
      if (schemaNode.used_by?.length) {
        genericSchemaMapping[schemaNode.name] = schemaNode.used_by;
      }
    });
    setGenericSchema(genericSchemaMapping);
  }, [
    fetchSchema,
    setGenericSchema,
    setSchema,
    setSchemaKindNameState,
    setGenerics,
  ]);

  useEffect(() => {
    setSchemaInState();
  }, [setSchemaInState, branch]);

  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          {MAIN_ROUTES.map((route) => (
            <Route
              index
              key={route.path}
              path={route.path}
              element={route.element}
            />
          ))}

          {CUSTOM_COMPONENT_ROUTES.map((route) => (
            <Route
              index
              key={route.path}
              path={route.path}
              element={route.element}
            />
          ))}
        </Route>
      </Routes>
      <ToastContainer
        hideProgressBar={true}
        transition={Slide}
        autoClose={5000}
        closeOnClick={false}
        newestOnTop
        position="bottom-right"
      />
    </>
  );
}

export default App;
