import { createHashRouter } from "react-router";
import Root from "./Root";
import Home from "../pages/Home";
import Reader from "../pages/Reader";
import Accuracy from "../pages/Accuracy";
import HowItWorks from "../pages/HowItWorks";
import Expired from "../pages/Expired";
import Gallery from "../pages/Gallery";

export const router = createHashRouter([
  { path: "/gallery", Component: Gallery },
  {
    path: "/",
    Component: Root,
    children: [
      { index: true, Component: Home },
      { path: "review/:documentId", Component: Reader },
      { path: "accuracy", Component: Accuracy },
      { path: "how-it-works", Component: HowItWorks },
      { path: "expired", Component: Expired },
      { path: "*", Component: Expired },
    ],
  },
]);
