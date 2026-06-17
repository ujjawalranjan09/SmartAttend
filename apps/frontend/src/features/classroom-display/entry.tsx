import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ClassroomDisplayPage } from "./ClassroomDisplayPage";
import "@/styles/globals.css";

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 5_000, refetchInterval: 5_000, retry: 0 } } });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <ClassroomDisplayPage />
    </QueryClientProvider>
  </React.StrictMode>
);
