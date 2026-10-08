import React, { useRef } from 'react';
import {
  FileText,
  Download,
  Upload,
  Eye,
  RotateCcw,
} from 'lucide-react';
import { DocumentData } from '../types';

interface NavbarProps {
  data: DocumentData;
  onUpdateTitle: (newTitle: string) => void;
  onUploadJson: (file: File) => void;
  onDownloadJson: () => void;
  onOpenPreview: () => void;
  onResetSeed: () => void;
  saveStatus: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  data,
  onUpdateTitle,
  onUploadJson,
  onDownloadJson,
  onOpenPreview,
  onResetSeed,
  saveStatus,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUploadJson(file);
      e.target.value = '';
    }
  };

  return (
    <header className="h-14 bg-white border-b border-[#e5ebe7] px-4 md:px-6 flex items-center justify-between shrink-0 select-none">
      {/* Left: Document Title */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-8 h-8 rounded-xl bg-[#154734] flex items-center justify-center text-white shrink-0 shadow-[0_2px_6px_rgba(21,71,52,0.2)]">
          <FileText className="w-4 h-4" />
        </div>

        <div className="flex flex-col min-w-0">
          <input
            type="text"
            value={data.root.title || ''}
            onChange={(e) => onUpdateTitle(e.target.value)}
            placeholder="Untitled Document"
            className="text-base font-semibold text-neutral-900 bg-transparent hover:bg-[#f4f7f5] focus:bg-white focus:outline-none focus:ring-1.5 focus:ring-[#154734] rounded-lg px-2 py-0.5 tracking-tight truncate max-w-xs sm:max-w-md transition"
          />
          <div className="flex items-center gap-2 text-[11px] text-neutral-400 px-2">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#2d6a4f]" />
              <span className="text-neutral-500 font-medium">{saveStatus}</span>
            </span>
            <span>·</span>
            <button
              onClick={onResetSeed}
              className="hover:text-[#154734] transition cursor-pointer"
              title="Reset to default seed policy"
            >
              Reset Seed
            </button>
          </div>
        </div>
      </div>

      {/* Right: Upload & Save Actions */}
      <div className="flex items-center gap-2 shrink-0">
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          onChange={handleFileChange}
          className="hidden"
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:text-[#154734] bg-white hover:bg-[#f2f7f4] border border-[#d8e2dc] hover:border-[#b7d5c5] rounded-xl transition shadow-2xs cursor-pointer"
          title="Upload an existing JSON outline file to render and edit"
        >
          <Upload className="w-3.5 h-3.5 text-neutral-500" />
          <span>Upload JSON</span>
        </button>

        <button
          onClick={onOpenPreview}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:text-[#154734] bg-white hover:bg-[#f2f7f4] border border-[#d8e2dc] hover:border-[#b7d5c5] rounded-xl transition shadow-2xs cursor-pointer"
          title="Preview entire outline JSON"
        >
          <Eye className="w-3.5 h-3.5 text-neutral-500" />
          <span>Preview</span>
        </button>

        <button
          onClick={onDownloadJson}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-[#154734] hover:bg-[#0f382c] rounded-xl shadow-[0_2px_8px_rgba(21,71,52,0.25)] transition cursor-pointer"
          title="Download updated outline tree JSON to local file"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Save JSON</span>
        </button>
      </div>
    </header>
  );
};
