"use client";

import ReactMarkdown from "react-markdown";

type Props = { content: string };

/**
 * Renders assistant (and similar) text that may include Markdown from the API, e.g. **bold**.
 */
export function ChatMarkdown({ content }: Props) {
  return (
    <div className="text-sm leading-relaxed [&_p]:mb-2 [&_p]:last:mb-0">
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 className="mb-2 mt-4 text-lg font-semibold tracking-tight text-zinc-900 first:mt-0 dark:text-zinc-50">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-2 mt-4 text-base font-semibold tracking-tight text-zinc-900 first:mt-0 dark:text-zinc-50">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-1.5 mt-3 text-sm font-semibold text-zinc-900 first:mt-0 dark:text-zinc-100">
              {children}
            </h3>
          ),
          p: ({ children }) => <p className="whitespace-pre-line">{children}</p>,
          strong: ({ children }) => (
            <strong className="font-semibold text-zinc-900 dark:text-zinc-100">
              {children}
            </strong>
          ),
          em: ({ children }) => <em className="italic opacity-90">{children}</em>,
          ul: ({ children }) => (
            <ul className="mb-2 list-outside list-disc space-y-1 pl-4 last:mb-0">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2 list-outside list-decimal space-y-1 pl-4 last:mb-0">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="pl-0.5">{children}</li>,
          a: ({ href, children }) => (
            <a
              href={href}
              className="font-medium text-indigo-600 underline decoration-indigo-500/30 underline-offset-2 hover:decoration-indigo-500 dark:text-indigo-400"
              rel="noopener noreferrer"
              target="_blank"
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
