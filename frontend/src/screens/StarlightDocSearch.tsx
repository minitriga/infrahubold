import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button, BUTTON_TYPES } from "../components/buttons/button";
import { PopOver, POPOVER_SIZE } from "../components/display/popover";
import { Icon } from "@iconify-icon/react";
import { Input } from "../components/inputs/input";
import * as pagefind from "../../../docs-starlight/dist/pagefind/pagefind";

export const StarlightDocSearch = () => {
  const [result, setResult] = useState([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (query === "") return;

    pagefind.search(query).then(({ results }) => {
      setResult(results.map(({ data, id }) => ({ data, id })));
    });
  }, [query]);

  return (
    <div className="relative">
      <PopOver buttonComponent={HelpButton} height={POPOVER_SIZE.LARGE}>
        {() => (
          <div>
            <Input placeholder="Search Docs" onChange={setQuery} />

            {query !== "" && <DisplayResults results={result} />}
          </div>
        )}
      </PopOver>
    </div>
  );
};

const HelpButton = () => <Button type="submit">Starlight</Button>;

const DisplayResults = ({
  results,
}: {
  results: Array<{
    id: string;
    data: () => Promise<{ excerpt: string; raw_url: string; meta: { title: string } }>;
  }>;
}) => {
  console.log(results);
  const [itemsToShow, setItemsToShow] = useState<number>(5);

  const handleLoadMore = () => {
    setItemsToShow((prevItems) => prevItems + 5);
  };

  return (
    <div>
      {results.slice(0, itemsToShow).map(({ id, data }) => (
        <Result key={id} data={data} />
      ))}
      <Button onClick={handleLoadMore} className="w-full !block">
        Load More Results
      </Button>
    </div>
  );
};

const Result = ({
  data,
}: {
  data: () => Promise<{ excerpt: string; raw_url: string; meta: { title: string } }>;
}) => {
  const [res, setRes] = useState();

  useEffect(() => {
    data().then(setRes);
  }, []);

  if (!res) return null;

  return (
    <div className="border-b p-2">
      <Link to={"http://localhost:4321" + res.raw_url} target="_blank">
        <h3 className="font-semibold">{res.meta.title}</h3>
        <p
          className="truncate overflow-ellipsis"
          dangerouslySetInnerHTML={{ __html: res.excerpt }}
        />
      </Link>
    </div>
  );
};
