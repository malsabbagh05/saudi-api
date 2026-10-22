"use client";

import { CopyButton } from "@/components/copy-button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type Example = { language: "curl" | "python" | "javascript"; code: string };

const LABELS: Record<Example["language"], string> = {
  curl: "curl",
  python: "Python",
  javascript: "JavaScript",
};

/** Request examples in curl, Python and JavaScript; code stays left-to-right in Arabic. */
export function CodeExamples({
  examples,
  copy,
  copied,
}: {
  examples: Example[];
  copy: string;
  copied: string;
}) {
  if (examples.length === 0) return null;
  return (
    <Tabs defaultValue={examples[0].language} className="gap-0">
      <TabsList variant="line" className="h-auto gap-0 border-b border-border p-0">
        {examples.map((example) => (
          <TabsTrigger
            key={example.language}
            value={example.language}
            className="rounded-none border-0 border-b-2 border-transparent px-3 py-1.5 text-xs data-[state=active]:border-primary data-[state=active]:text-foreground"
          >
            {LABELS[example.language]}
          </TabsTrigger>
        ))}
      </TabsList>
      {examples.map((example) => (
        <TabsContent key={example.language} value={example.language} className="mt-0">
          <CodeBlock code={example.code} copy={copy} copied={copied} />
        </TabsContent>
      ))}
    </Tabs>
  );
}

export function CodeBlock({
  code,
  copy,
  copied,
  wrap = false,
}: {
  code: string;
  copy: string;
  copied: string;
  /** Wrap long lines: for one-line commands that should read whole, not scroll. */
  wrap?: boolean;
}) {
  return (
    <div dir="ltr" className="rounded-sm bg-code-bg text-code-fg">
      <div className="flex justify-end border-b border-white/10 px-2 py-1">
        <CopyButton text={code} label={copy} done={copied} />
      </div>
      <pre
        className={`px-4 py-3 text-[0.8rem] leading-relaxed ${wrap ? "whitespace-pre-wrap [overflow-wrap:anywhere]" : "overflow-x-auto"}`}
      >
        <code>{code}</code>
      </pre>
    </div>
  );
}
