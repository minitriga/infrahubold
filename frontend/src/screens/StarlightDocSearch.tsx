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
      setResult(results.map(({ data }) => data));
    });
  }, [query]);

  return (
    <div className="relative">
      <PopOver buttonComponent={HelpButton} height={POPOVER_SIZE.LARGE}>
        {() => (
          <div>
            <Input placeholder="Search Docs" onChange={setQuery} />

            {query !== "" && <DisplayResults data={result} />}
          </div>
        )}
      </PopOver>
    </div>
  );
};

const HelpButton = () => <Button type="submit">Starlight</Button>;

const DisplayResults = ({
  data,
}: {
  data: Array<() => Promise<{ excerpt: string; raw_url: string; meta: { title: string } }>>;
}) => {
  const [visibleData, setVisibleData] = useState<
    Array<{ excerpt: string; raw_url: string; meta: { title: string } }>
  >([]);
  const [itemsToShow, setItemsToShow] = useState<number>(5);

  const fetchData = async () => {
    const results = await Promise.all(data.slice(0, itemsToShow).map((f) => f()));
    setVisibleData(results);
  };

  useEffect(() => {
    fetchData();
  }, []); // Fetch on the initial render

  const handleLoadMore = () => {
    setItemsToShow((prevItems) => prevItems + 5);
    fetchData();
  };

  return (
    <div>
      {visibleData.map((item, index) => (
        <div key={index} className="border-b p-2">
          <Link to={"http://localhost:4321" + item.raw_url} target="_blank">
            <h3 className="font-semibold">{item.meta.title}</h3>
            <p
              className="truncate overflow-ellipsis"
              dangerouslySetInnerHTML={{ __html: item.excerpt }}
            />
          </Link>
        </div>
      ))}
      <Button onClick={handleLoadMore} className="w-full !block">
        Load More Results
      </Button>
    </div>
  );
};
