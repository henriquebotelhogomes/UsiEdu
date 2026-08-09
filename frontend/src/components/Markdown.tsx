import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

/**
 * Mapeamento de componentes do Markdown (T7.1 / RF2-01).
 * - Links abrem em nova aba com rel seguro (noopener noreferrer).
 * - Tabelas ganham wrapper com rolagem horizontal.
 * - HTML cru nunca é executado (sem rehype-raw; conteúdo passa como texto).
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
      <table>{children}</table>
    </div>
  ),
  code: ({ node: _node, className, children }) => (
    <code className={className}>{children}</code>
  ),
  a: ({ node: _node, children, ...props }) => (
    <a target="_blank" rel="noopener noreferrer" {...props}>
      {children}
    </a>
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
