import { Metadata } from "next"

export const metadata: Metadata = {
  title: "Evaluations - Primus Documentation",
  description: "Learn about Evaluations in Primus - how content is assessed using scorecards"
}

export default function EvaluationsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
} 