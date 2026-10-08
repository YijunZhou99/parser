import { DocumentData } from '../types';

/**
 * Generate a standalone, zero-dependency HTML file containing the document outline annotator
 * and the current golden data JSON, capable of running natively or via python -m http.server.
 */
export function generateStandaloneHtml(data: DocumentData): string {
  const jsonStr = JSON.stringify(data, null, 2);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${data.root.title || 'Document Outline Annotator'}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .drag-over { border-top: 2px solid #2563eb !important; }
    .drag-inside { background-color: #eff6ff !important; outline: 2px dashed #3b82f6 !important; }
  </style>
</head>
<body class="bg-neutral-100 text-neutral-800 h-screen flex flex-col overflow-hidden">
  <!-- Top Navigation -->
  <header class="h-14 bg-white border-b border-neutral-200 px-6 flex items-center justify-between shrink-0">
    <div class="flex items-center gap-3">
      <span class="font-bold text-neutral-900 text-lg">Document Outline</span>
      <span class="text-xs px-2 py-0.5 bg-neutral-100 text-neutral-600 rounded">Standalone Version</span>
    </div>
    <div class="flex items-center gap-2">
      <button onclick="downloadJson()" class="px-3 py-1.5 text-xs font-medium bg-neutral-900 text-white rounded hover:bg-neutral-800 transition">
        Download JSON
      </button>
      <button onclick="copyJson()" id="copyBtn" class="px-3 py-1.5 text-xs font-medium border border-neutral-300 rounded hover:bg-neutral-50 transition">
        Copy JSON
      </button>
    </div>
  </header>

  <!-- Main View -->
  <div class="flex flex-1 overflow-hidden">
    <!-- Left Sidebar: Outline -->
    <aside class="w-80 bg-white border-r border-neutral-200 flex flex-col overflow-hidden shrink-0">
      <div class="p-3 border-b border-neutral-100 flex items-center justify-between">
        <span class="text-xs font-bold uppercase tracking-wider text-neutral-500">Document Outline</span>
        <button onclick="addRootChild()" class="text-xs px-2 py-1 bg-neutral-100 hover:bg-neutral-200 rounded font-medium text-neutral-700">
          + Add Section
        </button>
      </div>
      <div id="outlineList" class="flex-1 overflow-y-auto p-2 space-y-1"></div>
    </aside>

    <!-- Center: Google Docs Paper Editor -->
    <main class="flex-1 overflow-y-auto p-8 flex justify-center">
      <div class="w-full max-w-4xl bg-white shadow-sm border border-neutral-200/80 rounded-sm p-12 min-h-[800px]">
        <input id="docTitle" class="w-full text-3xl font-bold text-neutral-900 border-none focus:outline-none mb-4 pb-2 border-b border-transparent focus:border-neutral-300" oninput="updateDocTitle(this.value)" />
        <textarea id="docPreface" class="w-full text-sm text-neutral-600 border border-neutral-200 rounded p-2 focus:outline-none mb-8 resize-none" rows="2" placeholder="Document seed or preface text..." oninput="updateDocPreface(this.value)"></textarea>

        <div id="sectionsContainer" class="space-y-6"></div>
      </div>
    </main>
  </div>

  <script>
    let currentData = ${jsonStr};
    let draggedId = null;

    function render() {
      document.getElementById('docTitle').value = currentData.root.title;
      document.getElementById('docPreface').value = currentData.root.text;
      renderOutline();
      renderSections();
    }

    function renderOutline() {
      const container = document.getElementById('outlineList');
      container.innerHTML = '';

      function renderItem(node) {
        const item = document.createElement('div');
        item.draggable = true;
        item.className = 'group flex items-center justify-between py-1.5 px-2 rounded hover:bg-neutral-100 text-xs cursor-pointer select-none transition';
        item.style.paddingLeft = (node.depth * 14 + 6) + 'px';

        item.ondragstart = (e) => {
          draggedId = node.id;
          e.dataTransfer.setData('text/plain', node.id);
        };
        item.ondragover = (e) => {
          e.preventDefault();
          item.classList.add('drag-over');
        };
        item.ondragleave = () => {
          item.classList.remove('drag-over');
        };
        item.ondrop = (e) => {
          e.preventDefault();
          item.classList.remove('drag-over');
          if (draggedId && draggedId !== node.id) {
            moveNode(draggedId, node.id);
          }
        };

        item.onclick = () => {
          const el = document.getElementById('sec-' + node.id);
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        };

        const left = document.createElement('div');
        left.className = 'flex items-center gap-1.5 truncate flex-1';
        if (node.label) {
          const labelSpan = document.createElement('span');
          labelSpan.className = 'font-mono text-[11px] text-neutral-500 font-semibold';
          labelSpan.innerText = node.label;
          left.appendChild(labelSpan);
        }
        const titleSpan = document.createElement('span');
        titleSpan.className = 'font-medium text-neutral-800 truncate';
        titleSpan.innerText = node.title || '(Untitled)';
        left.appendChild(titleSpan);
        item.appendChild(left);

        const actions = document.createElement('div');
        actions.className = 'hidden group-hover:flex items-center gap-1 shrink-0';
        actions.innerHTML = \`
          <button title="Add subsection" onclick="event.stopPropagation(); addChild('\${node.id}')" class="px-1 text-neutral-500 hover:text-neutral-800 font-bold">+</button>
          <button title="Delete" onclick="event.stopPropagation(); deleteNode('\${node.id}')" class="px-1 text-red-500 hover:text-red-700">×</button>
        \`;
        item.appendChild(actions);

        container.appendChild(item);
        (node.children || []).forEach(renderItem);
      }

      (currentData.root.children || []).forEach(renderItem);
    }

    function renderSections() {
      const container = document.getElementById('sectionsContainer');
      container.innerHTML = '';

      function renderNode(node) {
        const sec = document.createElement('div');
        sec.id = 'sec-' + node.id;
        sec.className = 'border-l-2 pl-4 py-2 transition duration-200 border-neutral-200 focus-within:border-blue-500';
        sec.style.marginLeft = (Math.max(0, node.depth - 1) * 20) + 'px';

        const head = document.createElement('div');
        head.className = 'flex items-center gap-2 mb-2';

        const labelInput = document.createElement('input');
        labelInput.className = 'font-mono text-xs w-16 px-1.5 py-0.5 border border-neutral-200 rounded text-neutral-700 font-semibold focus:outline-none focus:border-blue-500';
        labelInput.value = node.label || '';
        labelInput.placeholder = 'Label';
        labelInput.oninput = (e) => { node.label = e.target.value; renderOutline(); };

        const titleInput = document.createElement('input');
        const headingSizes = ['text-2xl', 'text-xl', 'text-lg', 'text-base', 'text-sm'];
        const sizeClass = headingSizes[Math.min(node.depth - 1, headingSizes.length - 1)] || 'text-base';
        titleInput.className = \`flex-1 font-semibold text-neutral-900 border-b border-transparent hover:border-neutral-200 focus:border-blue-500 focus:outline-none pb-0.5 \${sizeClass}\`;
        titleInput.value = node.title || '';
        titleInput.placeholder = 'Section Title...';
        titleInput.oninput = (e) => { node.title = e.target.value; renderOutline(); };

        head.appendChild(labelInput);
        head.appendChild(titleInput);
        sec.appendChild(head);

        const bodyArea = document.createElement('textarea');
        bodyArea.className = 'w-full text-sm text-neutral-700 border border-transparent hover:border-neutral-200 focus:border-blue-400 focus:bg-neutral-50/50 rounded p-2 focus:outline-none resize-y min-h-[60px] font-sans leading-relaxed';
        bodyArea.value = node.text || '';
        bodyArea.placeholder = 'Body text or content...';
        bodyArea.oninput = (e) => { node.text = e.target.value; };
        sec.appendChild(bodyArea);

        container.appendChild(sec);
        (node.children || []).forEach(renderNode);
      }

      (currentData.root.children || []).forEach(renderNode);
    }

    function updateDocTitle(v) { currentData.root.title = v; }
    function updateDocPreface(v) { currentData.root.text = v; }

    function findAndParent(node, id, parent = null, index = -1) {
      if (node.id === id) return { node, parent, index };
      for (let i = 0; i < (node.children || []).length; i++) {
        const found = findAndParent(node.children[i], id, node, i);
        if (found.node) return found;
      }
      return { node: null, parent: null, index: -1 };
    }

    function recompute(node, depth = 0) {
      node.depth = depth;
      (node.children || []).forEach(c => recompute(c, depth + 1));
    }

    function addChild(id) {
      const found = findAndParent(currentData.root, id);
      if (!found.node) return;
      const newId = (found.node.label || '1') + '-' + Math.random().toString(16).slice(2, 8);
      found.node.children.push({
        id: newId,
        label: found.node.label ? found.node.label + '.' + (found.node.children.length + 1) : '' + (found.node.children.length + 1),
        title: 'New Section',
        text: '',
        depth: found.node.depth + 1,
        children: []
      });
      recompute(currentData.root, 0);
      render();
    }

    function addRootChild() {
      const newId = '' + (currentData.root.children.length + 1) + '-' + Math.random().toString(16).slice(2, 8);
      currentData.root.children.push({
        id: newId,
        label: '' + (currentData.root.children.length + 1),
        title: 'New Section',
        text: '',
        depth: 1,
        children: []
      });
      recompute(currentData.root, 0);
      render();
    }

    function deleteNode(id) {
      const found = findAndParent(currentData.root, id);
      if (found.parent) {
        found.parent.children.splice(found.index, 1);
        recompute(currentData.root, 0);
        render();
      }
    }

    function moveNode(dragId, targetId) {
      if (dragId === targetId) return;
      const d = findAndParent(currentData.root, dragId);
      const t = findAndParent(currentData.root, targetId);
      if (!d.node || !d.parent || !t.node) return;

      const [removed] = d.parent.children.splice(d.index, 1);
      if (t.parent) {
        t.parent.children.splice(t.index + 1, 0, removed);
      } else {
        t.node.children.push(removed);
      }
      recompute(currentData.root, 0);
      render();
    }

    function downloadJson() {
      const blob = new Blob([JSON.stringify(currentData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = (currentData.root.title || 'outline_tree').toLowerCase().replace(/[^a-z0-9]/g, '_') + '.json';
      a.click();
      URL.revokeObjectURL(url);
    }

    function copyJson() {
      navigator.clipboard.writeText(JSON.stringify(currentData, null, 2));
      const btn = document.getElementById('copyBtn');
      btn.innerText = 'Copied!';
      setTimeout(() => { btn.innerText = 'Copy JSON'; }, 1800);
    }

    render();
  </script>
</body>
</html>`;
}
