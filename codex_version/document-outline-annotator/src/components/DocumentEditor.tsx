import React, { useEffect } from 'react';
import {
  Plus,
  Trash2,
  ArrowRight,
  ArrowLeft,
} from 'lucide-react';
import { OutlineNode } from '../types';

interface DocumentEditorProps {
  root: OutlineNode;
  activeNodeId: string | null;
  onUpdateRoot: (updates: { title?: string; text?: string }) => void;
  onUpdateNode: (nodeId: string, updates: Partial<OutlineNode>) => void;
  onAddChild: (parentId: string) => void;
  onAddSibling: (siblingId: string) => void;
  onIndentNode: (nodeId: string) => void;
  onOutdentNode: (nodeId: string) => void;
  onDeleteNode: (nodeId: string) => void;
}

export const DocumentEditor: React.FC<DocumentEditorProps> = ({
  root,
  activeNodeId,
  onUpdateRoot,
  onUpdateNode,
  onAddChild,
  onAddSibling,
  onIndentNode,
  onOutdentNode,
  onDeleteNode,
}) => {
  // Smooth scroll into view when activeNodeId changes
  useEffect(() => {
    if (activeNodeId && activeNodeId !== 'root') {
      const el = document.getElementById(`section-${activeNodeId}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [activeNodeId]);

  const renderSection = (node: OutlineNode): React.ReactNode => {
    const isActive = activeNodeId === node.id;
    const depth = node.depth;

    let headingStyle = 'text-xl font-bold text-neutral-900';
    if (depth === 1) {
      headingStyle = 'text-2xl font-bold text-neutral-900 tracking-tight';
    } else if (depth === 2) {
      headingStyle = 'text-lg font-semibold text-neutral-800';
    } else if (depth >= 3) {
      headingStyle = 'text-base font-medium text-neutral-800';
    }

    const indentMargin = Math.max(0, depth - 1) * 20;

    return (
      <div
        key={node.id}
        id={`section-${node.id}`}
        style={{ marginLeft: `${indentMargin}px` }}
        className={`group relative pl-4 pr-2 py-3 rounded-xl border-l-2 transition-all duration-150 ${
          isActive
            ? 'border-[#154734] bg-[#f7faf8]'
            : 'border-neutral-200/90 hover:border-[#b7d5c5] focus-within:border-[#154734]'
        }`}
      >
        {/* Section Header */}
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {/* Label input */}
            <input
              type="text"
              value={node.label || ''}
              placeholder="Label"
              title="Section label (e.g. 1, 2.1, (a))"
              onChange={(e) => onUpdateNode(node.id, { label: e.target.value })}
              className="font-mono text-xs w-16 px-1.5 py-1 bg-white border border-[#d8e2dc] rounded-lg text-[#154734] font-bold focus:outline-none focus:border-[#154734] focus:ring-1 focus:ring-[#154734] shrink-0"
            />

            {/* Title input */}
            <input
              type="text"
              value={node.title || ''}
              placeholder="Section Title..."
              title="Section Title"
              onChange={(e) => onUpdateNode(node.id, { title: e.target.value })}
              className={`flex-1 bg-transparent border-b border-transparent hover:border-[#d8e2dc] focus:border-[#154734] focus:outline-none pb-0.5 ${headingStyle}`}
            />
          </div>

          {/* Clean Quick Actions */}
          <div className="opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex items-center gap-1 shrink-0 bg-white/95 border border-[#e2efe9] shadow-2xs p-0.5 rounded-lg">
            <button
              onClick={() => onOutdentNode(node.id)}
              title="Outdent"
              className="p-1 text-neutral-400 hover:text-[#154734] hover:bg-[#e8f3ee] rounded-md transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onIndentNode(node.id)}
              title="Indent"
              className="p-1 text-neutral-400 hover:text-[#154734] hover:bg-[#e8f3ee] rounded-md transition"
            >
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onAddChild(node.id)}
              title="Add Subsection"
              className="flex items-center gap-1 px-2 py-0.5 text-xs text-[#154734] bg-[#e8f3ee] hover:bg-[#d8ebd1] rounded-md font-semibold transition"
            >
              <Plus className="w-3 h-3" />
              <span>Sub</span>
            </button>
            <button
              onClick={() => onAddSibling(node.id)}
              title="Add Section Below"
              className="flex items-center gap-1 px-2 py-0.5 text-xs text-neutral-700 bg-neutral-100 hover:bg-neutral-200 rounded-md font-medium transition"
            >
              <Plus className="w-3 h-3" />
              <span>Below</span>
            </button>
            <button
              onClick={() => onDeleteNode(node.id)}
              title="Delete Section"
              className="p-1 text-rose-500 hover:bg-rose-50 rounded-md transition"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Section Body Textarea */}
        <textarea
          value={node.text || ''}
          placeholder="Section text or content..."
          onChange={(e) => onUpdateNode(node.id, { text: e.target.value })}
          rows={Math.max(2, (node.text || '').split('\n').length)}
          className="w-full text-sm text-neutral-700 border border-transparent hover:border-[#d8e2dc] focus:border-[#2d6a4f] focus:bg-[#fbfdfb] rounded-xl p-2.5 focus:outline-none resize-y min-h-[48px] font-sans leading-relaxed transition"
        />

        {/* Nested Children */}
        {node.children && node.children.length > 0 && (
          <div className="mt-2 space-y-2">
            {node.children.map((child) => renderSection(child))}
          </div>
        )}
      </div>
    );
  };

  return (
    <main className="flex-1 overflow-y-auto bg-[#f2f5f3] w-full min-w-0 p-4 sm:p-8">
      {/* Paper Canvas */}
      <div className="w-full max-w-4xl mx-auto bg-white shadow-[0_4px_24px_rgba(21,71,52,0.06)] border border-[#e2e8e4] rounded-2xl p-8 sm:p-14 min-h-[960px] flex flex-col mb-16">
        {/* Document Header (Title & Seed Text) */}
        <div className="mb-6 pb-6 border-b border-[#e5ebe7]">
          <input
            type="text"
            value={root.title || ''}
            placeholder="Document Title"
            onChange={(e) => onUpdateRoot({ title: e.target.value })}
            className="w-full text-3xl font-bold text-neutral-900 border-none hover:bg-[#f6f9f7] focus:bg-white focus:outline-none focus:ring-1.5 focus:ring-[#154734] rounded-xl px-2 py-1 tracking-tight"
          />

          <div className="mt-2">
            <textarea
              value={root.text || ''}
              placeholder="Document seed or preface text..."
              onChange={(e) => onUpdateRoot({ text: e.target.value })}
              rows={2}
              className="w-full text-sm text-neutral-600 bg-[#f8faf8] hover:bg-[#f3f7f4] focus:bg-white border border-[#d8e2dc] rounded-xl p-2.5 focus:outline-none focus:ring-1.5 focus:ring-[#154734] font-sans leading-relaxed resize-y"
            />
          </div>
        </div>

        {/* Sections */}
        <div className="space-y-3 flex-1">
          {root.children && root.children.length > 0 ? (
            root.children.map((child) => renderSection(child))
          ) : (
            <div className="py-16 text-center border-2 border-dashed border-[#d8e2dc] rounded-2xl">
              <p className="text-neutral-500 text-sm mb-3">No sections yet.</p>
              <button
                onClick={() => onAddChild('root')}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-[#154734] hover:bg-[#0f382c] rounded-xl transition cursor-pointer shadow-xs"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Section</span>
              </button>
            </div>
          )}
        </div>

        {/* Footer Add */}
        <div className="mt-10 pt-4 border-t border-[#e5ebe7] flex items-center justify-between text-xs text-neutral-400">
          <button
            onClick={() => onAddChild('root')}
            className="inline-flex items-center gap-1 text-[#154734] hover:text-[#0f382c] font-semibold"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Section at End</span>
          </button>
          <span>Document Outline Annotator</span>
        </div>
      </div>
    </main>
  );
};
