import React from 'react';

function formatInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|@\w+)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-gray-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code
          key={i}
          className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-gray-800"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('@')) {
      return (
        <span key={i} className="text-indigo-600 font-medium">
          {part}
        </span>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

export default function FormattedContent({ content }: { content: string }) {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];
  let listType: 'ul' | 'ol' | null = null;

  const flushList = () => {
    if (listItems.length > 0) {
      if (listType === 'ol') {
        elements.push(
          <ol
            key={`list-${elements.length}`}
            className="list-decimal ml-5 space-y-1 text-sm text-gray-700"
          >
            {listItems}
          </ol>,
        );
      } else {
        elements.push(
          <ul
            key={`list-${elements.length}`}
            className="list-disc ml-5 space-y-1 text-sm text-gray-700"
          >
            {listItems}
          </ul>,
        );
      }
      listItems = [];
      listType = null;
    }
  };

  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (trimmed === '') {
      flushList();
      return;
    }

    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(
        <h4 key={`h4-${i}`} className="font-semibold text-gray-900 text-sm mt-3 first:mt-0">
          {trimmed.slice(4)}
        </h4>,
      );
      return;
    }

    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(
        <h3 key={`h3-${i}`} className="font-semibold text-gray-900 mt-3 first:mt-0">
          {trimmed.slice(3)}
        </h3>,
      );
      return;
    }

    if (trimmed.startsWith('• ') || trimmed.startsWith('- ')) {
      if (listType !== 'ul') flushList();
      listType = 'ul';
      listItems.push(<li key={`li-${i}`}>{formatInline(trimmed.slice(2))}</li>);
      return;
    }

    const orderedMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (orderedMatch) {
      if (listType !== 'ol') flushList();
      listType = 'ol';
      listItems.push(<li key={`li-${i}`}>{formatInline(orderedMatch[2])}</li>);
      return;
    }

    flushList();
    elements.push(
      <p key={`p-${i}`} className="text-sm text-gray-700">
        {formatInline(trimmed)}
      </p>,
    );
  });

  flushList();

  return <div className="space-y-2">{elements}</div>;
}
