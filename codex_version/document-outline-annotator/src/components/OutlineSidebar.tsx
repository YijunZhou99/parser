import React, { useState } from 'react';
import {
  GripVertical,
  Plus,
  Trash2,
  ChevronRight,
  ChevronDown,
  ArrowRight,
  ArrowLeft,
} from 'lucide-react';
import { OutlineNode, DropPosition } from '../types';

interface OutlineSidebarProps {
  root: OutlineNode;
  activeNodeId: string | null;
  onSelectNode: (id: string) => void;
  onMoveNode: (dragId: string, targetId: string, position: DropPosition) => void;
  onAddChild: (parentId: string) => void;
  onIndentNode: (nodeId: string) => void;
  onOutdentNode: (nodeId: string) => void;
  onDeleteNode: (nodeId: string) => void;
}

export const OutlineSidebar: React.FC<OutlineSidebarProps> = ({
  root,
  activeNodeId,
  onSelectNode,
  onMoveNode,
  onAddChild,
  onIndentNode,
  onOutdentNode,
  onDeleteNode,
}) => {
  const [collapsedIds, setCollapsedIds] = useState<Record<string, boolean>>({});
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<{ id: string; position: DropPosition } | null>(null);

  const toggleCollapse = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCollapsedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleDragStart = (e: React.DragEvent, id: string) => {
    e.dataTransfer.setData('text/plain', id);
    e.dataTransfer.effectAllowed = 'move';
    setDraggedId(id);
  };

  const handleDragOver = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    if (!draggedId || draggedId === targetId) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const relativeY = e.clientY - rect.top;
    const height = rect.height;

    let position: DropPosition = 'after';
    if (relativeY < height * 0.28) {
      position = 'before';
    } else if (relativeY > height * 0.72) {
      position = 'after';
    } else {
      position = 'inside';
    }

    setDropTarget({ id: targetId, position });
  };

  const handleDragLeave = () => {
    setDropTarget(null);
  };

  const handleDrop = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    if (draggedId && dropTarget && dropTarget.id === targetId) {
      onMoveNode(draggedId, targetId, dropTarget.position);
    }
    setDraggedId(null);
    setDropTarget(null);
  };

  const handleDragEnd = () => {
    setDraggedId(null);
    setDropTarget(null);
  };

  const renderTreeItem = (node: OutlineNode): React.ReactNode => {
    const isCollapsed = !!collapsedIds[node.id];
    const hasChildren = node.children && node.children.length > 0;
    const isDraggingThis = draggedId === node.id;
    const isTarget = dropTarget && dropTarget.id === node.id;
    const isActive = activeNodeId === node.id;

    const indentPadding = Math.max(0, node.depth - 1) * 16 + 10;

    return (
      <div key={node.id} className="select-none">
        {/* Outline item row */}
        <div
          draggable
          onDragStart={(e) => handleDragStart(e, node.id)}
          onDragOver={(e) => handleDragOver(e, node.id)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, node.id)}
          onDragEnd={handleDragEnd}
          onClick={() => onSelectNode(node.id)}
          style={{ paddingLeft: `${indentPadding}px` }}
          className={`group relative flex items-center justify-between py-1.5 pr-2 rounded-xl text-xs cursor-pointer transition-all duration-100 ${
            isActive
              ? 'bg-[#e8f3ee] text-[#154734] font-semibold shadow-2xs'
              : 'text-neutral-700 hover:bg-[#f0f5f2] hover:text-[#154734]'
          } ${isDraggingThis ? 'opacity-30' : ''} ${
            isTarget && dropTarget.position === 'inside'
              ? 'bg-[#e8f3ee] ring-2 ring-[#154734] ring-inset'
              : ''
          }`}
        >
          {/* Drop line indicators */}
          {isTarget && dropTarget.position === 'before' && (
            <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#154734] rounded-full z-10" />
          )}
          {isTarget && dropTarget.position === 'after' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#154734] rounded-full z-10" />
          )}

          {/* Left item content */}
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            <div
              className="text-neutral-300 group-hover:text-[#2d6a4f] cursor-grab active:cursor-grabbing shrink-0"
              title="Drag to reorder"
            >
              <GripVertical className="w-3.5 h-3.5" />
            </div>

            {hasChildren ? (
              <button
                onClick={(e) => toggleCollapse(node.id, e)}
                className="w-4 h-4 flex items-center justify-center text-neutral-400 hover:text-[#154734] shrink-0"
              >
                {isCollapsed ? (
                  <ChevronRight className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
              </button>
            ) : (
              <div className="w-4 shrink-0" />
            )}

            {node.label && (
              <span className="font-mono text-[11px] font-semibold text-[#154734] bg-[#e2efe9]/70 px-1.5 py-0.5 rounded shrink-0">
                {node.label}
              </span>
            )}

            <span
              className={`truncate ${
                node.depth === 1 ? 'font-medium text-neutral-900' : 'text-neutral-700'
              }`}
            >
              {node.title || '(Untitled)'}
            </span>
          </div>

          {/* Minimal Quick Actions on Hover */}
          <div className="hidden group-hover:flex items-center gap-0.5 shrink-0 bg-white/95 border border-[#e2efe9] shadow-2xs px-1 py-0.5 rounded-lg">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onIndentNode(node.id);
              }}
              title="Indent (make child of previous)"
              className="p-0.5 text-neutral-500 hover:text-[#154734] rounded"
            >
              <ArrowRight className="w-3 h-3" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onOutdentNode(node.id);
              }}
              title="Outdent (promote level)"
              className="p-0.5 text-neutral-500 hover:text-[#154734] rounded"
            >
              <ArrowLeft className="w-3 h-3" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAddChild(node.id);
              }}
              title="Add subsection"
              className="p-0.5 text-[#154734] hover:bg-[#e8f3ee] rounded"
            >
              <Plus className="w-3 h-3" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteNode(node.id);
              }}
              title="Delete section"
              className="p-0.5 text-rose-500 hover:bg-rose-50 rounded"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Children nodes if not collapsed */}
        {hasChildren && !isCollapsed && (
          <div className="space-y-0.5">
            {node.children.map((child) => renderTreeItem(child))}
          </div>
        )}
      </div>
    );
  };

  return (
    <aside className="w-64 md:w-72 bg-[#fafbfa] border-r border-[#e5ebe7] flex flex-col h-full shrink-0 select-none">
      {/* Sidebar Header */}
      <div className="p-3.5 border-b border-[#e5ebe7] flex items-center justify-between shrink-0">
        <span className="text-xs font-bold uppercase tracking-wider text-[#154734]/80">
          Document Outline
        </span>
        <button
          onClick={() => onAddChild('root')}
          className="flex items-center gap-1 text-xs px-2.5 py-1 bg-[#e8f3ee] text-[#154734] hover:bg-[#d8ebd1] font-semibold rounded-xl transition cursor-pointer shadow-2xs"
          title="Add new section"
        >
          <Plus className="w-3 h-3" />
          <span>Section</span>
        </button>
      </div>

      {/* Outline List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {root.children.length === 0 ? (
          <div className="p-6 text-center text-neutral-400 text-xs">
            <p>No sections yet.</p>
            <button
              onClick={() => onAddChild('root')}
              className="mt-2 text-[#154734] hover:underline font-semibold"
            >
              + Add first section
            </button>
          </div>
        ) : (
          root.children.map((child) => renderTreeItem(child))
        )}
      </div>
    </aside>
  );
};
