/**
 * Same as JSON.stringify, but this will remove the quotes around keys/properties from the output
 *
 * const data = {a: 1, b: [{tags: ["Tag A"]}, {tags: ["Tag B"]}]}
 *
 * JSON.stringify(data)
 * '{"a":1,"b":[{"tags":["Tag A"]},{"tags":["Tag B"]}]}'
 *
 * stringifyWithoutQuotes(data)
 * '{a:1,b:[{tags:["Tag A"]},{tags:["Tag B"]}]}'
 */

export const stringifyWithoutQuotes = (obj: object): string => {
  return JSON.stringify(obj, null, 4).replace(/"([^"]+)":/g, "$1:");
};

export const cleanTabsAndNewLines = (string: string) => {
  return string.replaceAll(/\t*\n*/g, "").replaceAll(/\s+/g, " ");
};

export const displayTextWithNewLines = (string: string) =>
  string.split("\n").map((s: string, index: number) => <div key={index}>{s || <br />}</div>);