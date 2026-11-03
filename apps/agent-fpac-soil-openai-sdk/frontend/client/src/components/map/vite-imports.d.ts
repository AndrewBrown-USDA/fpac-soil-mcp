// The client tsconfig does not include `vite/client`, so declare the one Vite
// import suffix the map panel uses.
declare module '*?worker&url' {
  const url: string;
  export default url;
}
