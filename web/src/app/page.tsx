"use client";
import dynamic from "next/dynamic";

// The game touches window/WebGL, so it renders only in the browser.
const App = dynamic(() => import("@/ui/App"), { ssr: false });

export default function Page() {
  return <App />;
}
