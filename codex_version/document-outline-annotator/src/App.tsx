import React, { useState, useEffect, useCallback, useRef } from 'react';
import { DocumentData, OutlineNode, DropPosition } from './types';
import { PTO_POLICY_DATA } from './sampleData';
import {
  updateNodeInTree,
  addNodeToTree,
  deleteNodeFromTree,
  moveNodeInTree,
  indentNode,
  outdentNode,
  normalizeUploadedJson,
} from './utils/treeUtils';
import { Navbar } from './components/Navbar';
import { OutlineSidebar } from './components/OutlineSidebar';
import { DocumentEditor } from './components/DocumentEditor';
import { JsonPreviewModal } from './components/JsonPreviewModal';

const STORAGE_KEY = 'outline_annotator_data_simple';

export default function App() {
  const [data, setData] = useState<DocumentData>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed?.root?.children) {
          return normalizeUploadedJson(parsed);
        }
      }
    } catch (e) {
      // fallback
    }
    return PTO_POLICY_DATA;
  });

  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState('All changes saved');
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [reviewed, setReviewed] = useState(false);

  // Auto-save to localStorage
  const saveTimerRef = useRef<number | null>(null);
  useEffect(() => {
    setReviewed(false);
    setSaveStatus('Saving...');
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    saveTimerRef.current = window.setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        setSaveStatus('All changes saved');
      } catch (err) {
        setSaveStatus('Save error');
      }
    }, 300);

    return () => {
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    };
  }, [data]);

  // Upload JSON file handler
  const handleUploadJson = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const parsed = JSON.parse(content);
        const ids = new Set<string>();
        const check = (n: any, depth: number) => {
          if (!n || typeof n !== 'object' ||
              Object.keys(n).sort().join(',') !== 'children,depth,id,label,text,title' ||
              ['id', 'label', 'title', 'text'].some(k => typeof n[k] !== 'string') ||
              !n.id || ids.has(n.id) || n.depth !== depth || !Array.isArray(n.children)) {
            throw new Error('Invalid node schema, ID or depth; import was not normalized');
          }
          ids.add(n.id);
          n.children.forEach((c: any) => check(c, depth + 1));
        };
        if (Object.keys(parsed).join(',') !== 'root') throw new Error('Expected exactly {root}');
        check(parsed.root, 0);
        const normalized = normalizeUploadedJson(parsed);
        setData(normalized);
        setReviewed(false);
        setActiveNodeId(null);
        setSaveStatus(`Loaded ${file.name}`);
      } catch (err: any) {
        alert(`Failed to load JSON: ${err.message || 'Invalid format'}`);
      }
    };
    reader.readAsText(file);
  }, []);

  // Save / Download JSON file
  const handleDownloadJson = useCallback(() => {
    const cleanTitle = (data.root.title || 'outline_tree')
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '_');
    const filename = reviewed ? 'golden.json' : `${cleanTitle || 'outline'}.unreviewed.json`;

    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setSaveStatus('JSON downloaded');
  }, [data, reviewed]);

  // Reset to default PTO policy
  const handleResetSeed = useCallback(() => {
    if (window.confirm('Reset outline to seed PTO policy?')) {
      setData(PTO_POLICY_DATA);
      setActiveNodeId(null);
      setSaveStatus('Reset to seed');
    }
  }, []);

  // Drag & drop file onto the browser window
  useEffect(() => {
    const handleWindowDragOver = (e: DragEvent) => {
      if (e.dataTransfer?.types.includes('Files')) {
        e.preventDefault();
      }
    };

    const handleWindowDrop = (e: DragEvent) => {
      if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        if (file.name.endsWith('.json') || file.type === 'application/json') {
          e.preventDefault();
          handleUploadJson(file);
        }
      }
    };

    window.addEventListener('dragover', handleWindowDragOver);
    window.addEventListener('drop', handleWindowDrop);
    return () => {
      window.removeEventListener('dragover', handleWindowDragOver);
      window.removeEventListener('drop', handleWindowDrop);
    };
  }, [handleUploadJson]);

  // Keyboard shortcut Ctrl+S
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleDownloadJson();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleDownloadJson]);

  // Tree mutations
  const handleUpdateTitle = useCallback((title: string) => {
    setData((prev) => ({
      ...prev,
      root: { ...prev.root, title },
    }));
  }, []);

  const handleUpdateRoot = useCallback(
    (updates: { title?: string; text?: string }) => {
      setData((prev) => ({
        ...prev,
        root: { ...prev.root, ...updates },
      }));
    },
    []
  );

  const handleUpdateNode = useCallback(
    (nodeId: string, updates: Partial<OutlineNode>) => {
      setData((prev) => ({
        ...prev,
        root: updateNodeInTree(prev.root, nodeId, updates),
      }));
    },
    []
  );

  const handleAddChild = useCallback((parentId: string) => {
    setData((prev) => {
      const res = addNodeToTree(prev.root, parentId, 'asChild');
      setActiveNodeId(res.newNodeId);
      return { ...prev, root: res.updatedRoot };
    });
  }, []);

  const handleAddSibling = useCallback((siblingId: string) => {
    setData((prev) => {
      const res = addNodeToTree(prev.root, siblingId, 'asSiblingAfter');
      setActiveNodeId(res.newNodeId);
      return { ...prev, root: res.updatedRoot };
    });
  }, []);

  const handleMoveNode = useCallback(
    (dragId: string, targetId: string, position: DropPosition) => {
      setData((prev) => ({
        ...prev,
        root: moveNodeInTree(prev.root, dragId, targetId, position),
      }));
    },
    []
  );

  const handleIndentNode = useCallback((nodeId: string) => {
    setData((prev) => ({
      ...prev,
      root: indentNode(prev.root, nodeId),
    }));
  }, []);

  const handleOutdentNode = useCallback((nodeId: string) => {
    setData((prev) => ({
      ...prev,
      root: outdentNode(prev.root, nodeId),
    }));
  }, []);

  const handleDeleteNode = useCallback((nodeId: string) => {
    setData((prev) => ({
      ...prev,
      root: deleteNodeFromTree(prev.root, nodeId),
    }));
  }, []);

  return (
    <div className="flex flex-col h-full w-full bg-[#f2f5f3] overflow-hidden font-sans text-neutral-800 antialiased">
      <div className="px-4 py-2 bg-amber-100 text-sm flex gap-4 items-center">
        <span>Imported silver is an AI draft reference. Keep its original file. Review against the original PDF.</span>
        <label><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} /> I manually verified this tree against the PDF; download as reviewed golden.json</label>
      </div>
      {/* Super minimal Top Bar */}
      <Navbar
        data={data}
        onUpdateTitle={handleUpdateTitle}
        onUploadJson={handleUploadJson}
        onDownloadJson={handleDownloadJson}
        onOpenPreview={() => setIsPreviewOpen(true)}
        onResetSeed={handleResetSeed}
        saveStatus={saveStatus}
      />

      {/* Main Workspace: Left Outline + Google Docs Editor */}
      <div className="flex flex-1 overflow-hidden">
        <OutlineSidebar
          root={data.root}
          activeNodeId={activeNodeId}
          onSelectNode={(id) => setActiveNodeId(id)}
          onMoveNode={handleMoveNode}
          onAddChild={handleAddChild}
          onIndentNode={handleIndentNode}
          onOutdentNode={handleOutdentNode}
          onDeleteNode={handleDeleteNode}
        />

        <DocumentEditor
          root={data.root}
          activeNodeId={activeNodeId}
          onUpdateRoot={handleUpdateRoot}
          onUpdateNode={handleUpdateNode}
          onAddChild={handleAddChild}
          onAddSibling={handleAddSibling}
          onIndentNode={handleIndentNode}
          onOutdentNode={handleOutdentNode}
          onDeleteNode={handleDeleteNode}
        />
      </div>

      {/* JSON Preview Modal */}
      <JsonPreviewModal
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        data={data}
      />
    </div>
  );
}
