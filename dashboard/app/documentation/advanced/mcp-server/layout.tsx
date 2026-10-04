import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Primus MCP / Tactus Runtime - Primus Documentation",
  description: "Learn how Primus exposes one programmable MCP tool backed by the host-provided Primus Tactus runtime."
};

export default function McpServerLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
