import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { JobProvider } from "./context/JobContext";
import { ThemeProvider } from "./context/ThemeContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <JobProvider>
        <App />
      </JobProvider>
    </ThemeProvider>
  </StrictMode>
);