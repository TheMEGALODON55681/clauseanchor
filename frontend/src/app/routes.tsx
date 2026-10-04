import type { ComponentType } from "react";
import { createHashRouter, type RouteObject } from "react-router";
import Root from "./Root";
import RootError from "./RootError";
import Home from "../pages/Home";

/* Every page except the landing page loads on demand, so the landing page does
   not carry the reader. The previous page stays until the next one is ready. */
const page = (load: () => Promise<{ default: ComponentType }>) => ({
  lazy: async () => ({ Component: (await load()).default }),
});

const routes: RouteObject[] = [
  {
    path: "/",
    Component: Root,
    ErrorBoundary: RootError,
    HydrateFallback: () => null,
    children: [
      {
        // A failing page shows the error inside the shell.
        ErrorBoundary: RootError,
        children: [
          { index: true, Component: Home },
          { path: "review/:documentId", ...page(() => import("../pages/Reader")) },
          { path: "accuracy", ...page(() => import("../pages/Accuracy")) },
          { path: "how-it-works", ...page(() => import("../pages/HowItWorks")) },
          { path: "expired", ...page(() => import("../pages/Expired")) },
          { path: "*", ...page(() => import("../pages/NotFound")) },
        ],
      },
    ],
  },
  // The component gallery exists in development only. The dead branch is removed from a production build.
  ...(import.meta.env.DEV ? [{ path: "/gallery", HydrateFallback: () => null, ...page(() => import("../pages/Gallery")) }] : []),
];

export const router = createHashRouter(routes);
