import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "./index.css"
import App from "./App.tsx"
import { ThemeProvider } from "@/components/theme-provider.tsx"
import { TooltipProvider } from "@/components/ui/tooltip"
import { I18nProvider } from "@/lib/i18n"
import { StoreProvider } from "@/lib/store"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark">
      <I18nProvider>
        <StoreProvider>
          <TooltipProvider>
            <App />
          </TooltipProvider>
        </StoreProvider>
      </I18nProvider>
    </ThemeProvider>
  </StrictMode>
)
