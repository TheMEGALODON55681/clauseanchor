import { RouterProvider } from "react-router";
import { router } from "./app/routes";
import { ThemeProvider } from "./app/theme";
import { SessionProvider } from "./app/session";

export default function App() {
  return (
    <ThemeProvider>
      <SessionProvider>
        <RouterProvider router={router} />
      </SessionProvider>
    </ThemeProvider>
  );
}
