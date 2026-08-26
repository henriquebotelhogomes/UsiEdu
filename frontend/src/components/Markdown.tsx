import { useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

/**
 * Componente para blocos de código com botão de cópia (RF4-05).
 */
function CodeBlock({ className, children }: { className?: string; children: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const codeString = String(children).replace(/\n$/, "");
  const isInline = !className && !codeString.includes("\n");

  if (isInline) {
    return <code className="inline-code">{children}</code>;
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(codeString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block-container">
      <div className="code-block-header">
        <span className="code-lang">{className ? className.replace("language-", "") : "text"}</span>
        <button
          type="button"
          className="copy-btn"
          onClick={handleCopy}
          aria-label="Copiar código"
        >
          {copied ? "✓ Copiado" : "Copiar"}
        </button>
      </div>
      <pre className="code-pre">
        <code className={className}>{children}</code>
      </pre>
    </div>
  );
}

/**
 * Mapeamento de componentes do Markdown (T7.1 / RF4-05).
 */
const mdComponents: Components = {
  h1: ({ node: _node, children }) => <h1>{children}</h1>,
  h2: ({ node: _node, children }) => <h2>{children}</h2>,
  h3: ({ node: _node, children }) => <h3>{children}</h3>,
  h4: ({ node: _node, children }) => <h4>{children}</h4>,
  ul: ({ node: _node, children }) => <ul>{children}</ul>,
  ol: ({ node: _node, children }) => <ol>{children}</ol>,
  li: ({ node: _node, children }) => <li>{children}</li>,
  table: ({ node: _node, children }) => (
    <div className="md-table-wrap">
      <table className="styled-table">{children}</table>
    </div>
  ),
  code: ({ node: _node, className, children }) => (
    <CodeBlock className={className}>{children}</CodeBlock>
  ),
  a: ({ node: _node, children, ...props }) => (
    <a target="_blank" rel="noopener noreferrer" {...props}>
      {children}
    </a>
  ),
  blockquote: ({ node: _node, children }) => (
    <blockquote className="styled-blockquote">{children}</blockquote>
  ),
};

interface MarkdownProps {
  content: string;
}

export default function Markdown({ content }: MarkdownProps) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={mdComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
