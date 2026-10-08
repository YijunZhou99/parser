import React, { useState } from 'react';
import { X, Copy, Check, FileCode, Download } from 'lucide-react';
import { DocumentData } from '../types';

interface JsonPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: DocumentData;
}

export const JsonPreviewModal: React.FC<JsonPreviewModalProps> = ({
  isOpen,
  onClose,
  data,
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const jsonString = JSON.stringify(data, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const cleanTitle = (data.root.title || 'outline_tree')
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '_');
    const filename = `${cleanTitle || 'outline'}.json`;
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 select-none">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col border border-[#e2e8e4] overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#e5ebe7] flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#e8f3ee] text-[#154734] flex items-center justify-center shrink-0">
              <FileCode className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-neutral-900 text-sm tracking-tight">
                JSON Preview
              </h3>
              <p className="text-[11px] text-neutral-400">
                {data.root.title || 'Untitled'} · {jsonString.length.toLocaleString()} bytes
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl transition cursor-pointer shadow-2xs ${
                copied
                  ? 'bg-[#2d6a4f] text-white'
                  : 'bg-[#e8f3ee] hover:bg-[#d8ebd1] text-[#154734]'
              }`}
              title="Copy JSON to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy JSON</span>
                </>
              )}
            </button>

            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-[#154734] hover:bg-[#0f382c] rounded-xl shadow-xs transition cursor-pointer"
              title="Download JSON"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Save</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 text-neutral-400 hover:text-neutral-700 hover:bg-[#f2f7f4] rounded-xl transition cursor-pointer ml-1"
              title="Close preview"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Code Content View */}
        <div className="flex-1 overflow-auto p-4 bg-[#f8faf8] select-text">
          <pre className="font-mono text-xs text-neutral-800 leading-relaxed bg-white border border-[#e2e8e4] p-4 rounded-xl shadow-2xs overflow-x-auto whitespace-pre">
            {jsonString}
          </pre>
        </div>
      </div>
    </div>
  );
};
