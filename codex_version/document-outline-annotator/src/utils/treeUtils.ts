import { OutlineNode, DocumentData, DropPosition } from '../types';

export function generateRandomHex(length = 6): string {
  const chars = '0123456789abcdef';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars[Math.floor(Math.random() * chars.length)];
  }
  return result;
}

export function generateNodeId(label = 'sec'): string {
  const cleanLabel = (label || 'item')
    .replace(/[^a-zA-Z0-9.]/g, '')
    .slice(0, 10);
  return `${cleanLabel || 'item'}-${generateRandomHex(6)}`;
}

/**
 * Deep clone a node and recursively fix depths so that depth === parent.depth + 1
 */
export function recomputeDepths(node: OutlineNode, currentDepth = 0): OutlineNode {
  return {
    ...node,
    depth: currentDepth,
    children: (node.children || []).map((child) =>
      recomputeDepths(child, currentDepth + 1)
    ),
  };
}

/**
 * Deep clone an OutlineNode
 */
export function cloneTree(node: OutlineNode): OutlineNode {
  return {
    ...node,
    children: (node.children || []).map(cloneTree),
  };
}

/**
 * Safely parse and normalize an uploaded JSON into DocumentData
 */
export function normalizeUploadedJson(raw: any): DocumentData {
  const rootNode = raw?.root || raw;
  if (!rootNode || typeof rootNode !== 'object') {
    throw new Error('Invalid JSON format: missing root object');
  }

  function sanitizeNode(n: any, depth = 0): OutlineNode {
    return {
      id: String(n.id || (depth === 0 ? 'root' : generateNodeId(n.label))),
      label: String(n.label ?? ''),
      title: String(n.title ?? ''),
      text: String(n.text ?? ''),
      depth: typeof n.depth === 'number' ? n.depth : depth,
      children: Array.isArray(n.children)
        ? n.children.map((c: any) => sanitizeNode(c, depth + 1))
        : [],
    };
  }

  const root = sanitizeNode(rootNode, 0);
  return { root: recomputeDepths(root, 0) };
}

/**
 * Find a node and its parent + index in parent's children array
 */
export function findNodeAndParent(
  root: OutlineNode,
  targetId: string,
  parent: OutlineNode | null = null,
  index = -1
): { node: OutlineNode | null; parent: OutlineNode | null; index: number } {
  if (root.id === targetId) {
    return { node: root, parent, index };
  }

  for (let i = 0; i < root.children.length; i++) {
    const found = findNodeAndParent(root.children[i], targetId, root, i);
    if (found.node) {
      return found;
    }
  }

  return { node: null, parent: null, index: -1 };
}

/**
 * Update attributes of a node in the tree immutably
 */
export function updateNodeInTree(
  root: OutlineNode,
  targetId: string,
  partial: Partial<OutlineNode>
): OutlineNode {
  if (root.id === targetId) {
    return {
      ...root,
      ...partial,
      children: partial.children !== undefined ? partial.children : root.children,
    };
  }

  return {
    ...root,
    children: root.children.map((child) =>
      updateNodeInTree(child, targetId, partial)
    ),
  };
}

/**
 * Delete a node from the tree
 */
export function deleteNodeFromTree(root: OutlineNode, targetId: string): OutlineNode {
  if (root.id === targetId) {
    return root; // cannot delete root
  }

  const newRoot = cloneTree(root);
  const found = findNodeAndParent(newRoot, targetId);

  if (found.parent && found.index !== -1) {
    found.parent.children.splice(found.index, 1);
  }

  return recomputeDepths(newRoot, 0);
}

/**
 * Add a new node to the tree
 */
export function addNodeToTree(
  root: OutlineNode,
  referenceId: string,
  mode: 'asChild' | 'asSiblingAfter' | 'asSiblingBefore' = 'asSiblingAfter'
): { updatedRoot: OutlineNode; newNodeId: string } {
  const newRoot = cloneTree(root);
  const found = findNodeAndParent(newRoot, referenceId);

  let newLabel = '1';
  let newDepth = 1;

  if (mode === 'asChild') {
    const parentNode = found.node || newRoot;
    newDepth = parentNode.depth + 1;
    newLabel = parentNode.label ? `${parentNode.label}.${parentNode.children.length + 1}` : `${parentNode.children.length + 1}`;
    const newNode: OutlineNode = {
      id: generateNodeId(newLabel),
      label: newLabel,
      title: 'New Section',
      text: '',
      depth: newDepth,
      children: [],
    };
    parentNode.children.push(newNode);
    return { updatedRoot: recomputeDepths(newRoot, 0), newNodeId: newNode.id };
  }

  // Siblings
  const parentNode = found.parent || newRoot;
  const targetIndex = found.index !== -1 ? found.index : parentNode.children.length;
  newDepth = parentNode.depth + 1;
  newLabel = parentNode.label ? `${parentNode.label}.${targetIndex + 1}` : `${targetIndex + 1}`;

  const newNode: OutlineNode = {
    id: generateNodeId(newLabel),
    label: newLabel,
    title: 'New Section',
    text: '',
    depth: newDepth,
    children: [],
  };

  const insertIndex = mode === 'asSiblingBefore' ? targetIndex : targetIndex + 1;
  parentNode.children.splice(insertIndex, 0, newNode);

  return { updatedRoot: recomputeDepths(newRoot, 0), newNodeId: newNode.id };
}

/**
 * Move node (drag and drop)
 */
export function moveNodeInTree(
  root: OutlineNode,
  dragId: string,
  targetId: string,
  position: DropPosition
): OutlineNode {
  if (dragId === targetId || dragId === 'root') {
    return root;
  }

  const newRoot = cloneTree(root);

  // Check if target is a descendant of dragId
  const isDescendant = (node: OutlineNode, searchId: string): boolean => {
    if (node.id === searchId) return true;
    return node.children.some((c) => isDescendant(c, searchId));
  };

  const dragFound = findNodeAndParent(newRoot, dragId);
  if (!dragFound.node || !dragFound.parent) return root;

  if (isDescendant(dragFound.node, targetId)) {
    // Cannot move a parent into its own descendant!
    return root;
  }

  // Remove dragNode from its current parent
  const [draggedNode] = dragFound.parent.children.splice(dragFound.index, 1);

  // Find target again after removal
  const targetFound = findNodeAndParent(newRoot, targetId);
  if (!targetFound.node) {
    return root;
  }

  if (position === 'inside') {
    targetFound.node.children.push(draggedNode);
  } else if (position === 'before') {
    if (targetFound.parent) {
      targetFound.parent.children.splice(targetFound.index, 0, draggedNode);
    } else {
      // Root cannot have siblings, put as child
      targetFound.node.children.unshift(draggedNode);
    }
  } else if (position === 'after') {
    if (targetFound.parent) {
      targetFound.parent.children.splice(targetFound.index + 1, 0, draggedNode);
    } else {
      // Root cannot have siblings, put as child
      targetFound.node.children.push(draggedNode);
    }
  }

  return recomputeDepths(newRoot, 0);
}

/**
 * Indent node (make it the child of its previous sibling)
 */
export function indentNode(root: OutlineNode, targetId: string): OutlineNode {
  const newRoot = cloneTree(root);
  const found = findNodeAndParent(newRoot, targetId);

  if (!found.node || !found.parent || found.index <= 0) {
    return root; // No previous sibling to become child of
  }

  const prevSibling = found.parent.children[found.index - 1];
  const [nodeToMove] = found.parent.children.splice(found.index, 1);
  prevSibling.children.push(nodeToMove);

  return recomputeDepths(newRoot, 0);
}

/**
 * Outdent node (make it a sibling of its parent, placed right after the parent)
 */
export function outdentNode(root: OutlineNode, targetId: string): OutlineNode {
  const newRoot = cloneTree(root);
  const found = findNodeAndParent(newRoot, targetId);

  if (!found.node || !found.parent || found.parent.id === 'root') {
    return root; // Already at top level (depth 1) or invalid
  }

  const grandParentFound = findNodeAndParent(newRoot, found.parent.id);
  if (!grandParentFound.node) return root;

  const grandParent = grandParentFound.parent || newRoot;
  const parentIndex = grandParent.children.findIndex((c) => c.id === found.parent!.id);

  if (parentIndex === -1) return root;

  const [nodeToMove] = found.parent.children.splice(found.index, 1);
  grandParent.children.splice(parentIndex + 1, 0, nodeToMove);

  return recomputeDepths(newRoot, 0);
}

/**
 * Move node up within same parent
 */
export function moveNodeUp(root: OutlineNode, targetId: string): OutlineNode {
  const newRoot = cloneTree(root);
  const found = findNodeAndParent(newRoot, targetId);

  if (!found.node || !found.parent || found.index <= 0) {
    return root;
  }

  const temp = found.parent.children[found.index - 1];
  found.parent.children[found.index - 1] = found.parent.children[found.index];
  found.parent.children[found.index] = temp;

  return newRoot;
}

/**
 * Move node down within same parent
 */
export function moveNodeDown(root: OutlineNode, targetId: string): OutlineNode {
  const newRoot = cloneTree(root);
  const found = findNodeAndParent(newRoot, targetId);

  if (!found.node || !found.parent || found.index >= found.parent.children.length - 1) {
    return root;
  }

  const temp = found.parent.children[found.index + 1];
  found.parent.children[found.index + 1] = found.parent.children[found.index];
  found.parent.children[found.index] = temp;

  return newRoot;
}

/**
 * Automatically re-generate clean hierarchical labels (1, 1.1, 1.2, 2, 2.1, etc.)
 */
export function autoRenumberTree(node: OutlineNode, parentPrefix = ''): OutlineNode {
  const updatedChildren = (node.children || []).map((child, idx) => {
    const currentNumber = (idx + 1).toString();
    const newLabel = parentPrefix ? `${parentPrefix}.${currentNumber}` : currentNumber;
    return autoRenumberTree(
      {
        ...child,
        label: newLabel,
      },
      newLabel
    );
  });

  return {
    ...node,
    children: updatedChildren,
  };
}

/**
 * Flatten tree into an ordered array of nodes (excluding or including root)
 */
export function flattenOutline(node: OutlineNode, includeRoot = false): OutlineNode[] {
  const result: OutlineNode[] = [];
  if (includeRoot) {
    result.push(node);
  }

  function walk(current: OutlineNode) {
    for (const child of current.children) {
      result.push(child);
      walk(child);
    }
  }

  walk(node);
  return result;
}

/**
 * Validate golden data tree integrity
 */
export function validateTree(root: OutlineNode): {
  valid: boolean;
  issues: string[];
  stats: {
    totalNodes: number;
    maxDepth: number;
    wordCount: number;
    emptyTitles: number;
    duplicateIds: number;
  };
} {
  const issues: string[] = [];
  const ids = new Set<string>();
  let totalNodes = 0;
  let maxDepth = 0;
  let wordCount = (root.text || '').trim().split(/\s+/).filter(Boolean).length;
  let emptyTitles = 0;
  let duplicateIds = 0;

  function traverse(node: OutlineNode, expectedDepth: number, parentPath: string) {
    totalNodes++;
    if (node.depth > maxDepth) maxDepth = node.depth;

    if (ids.has(node.id)) {
      duplicateIds++;
      issues.push(`Duplicate ID found: "${node.id}" at ${parentPath}`);
    } else {
      ids.add(node.id);
    }

    if (!node.title.trim() && node.id !== 'root') {
      emptyTitles++;
      issues.push(`Node "${node.id}" (Label: ${node.label || 'None'}) has an empty title`);
    }

    if (node.depth !== expectedDepth) {
      issues.push(`Node "${node.id}" has depth ${node.depth}, expected ${expectedDepth}`);
    }

    if (node.text) {
      wordCount += node.text.trim().split(/\s+/).filter(Boolean).length;
    }

    const currentPath = parentPath ? `${parentPath} > ${node.label || node.title}` : node.title;

    for (const child of node.children) {
      traverse(child, expectedDepth + 1, currentPath);
    }
  }

  traverse(root, 0, 'Root');

  return {
    valid: issues.length === 0,
    issues,
    stats: {
      totalNodes,
      maxDepth,
      wordCount,
      emptyTitles,
      duplicateIds,
    },
  };
}

/**
 * Fast Raw Text Parser to Outline Tree
 * Parses text where sections are headed by markdown headings (#, ##, ###)
 * or numbered headers like "1 Scope", "1.1 Subsection", "2. Accrual"
 */
export function parseRawTextToTree(rawText: string, docTitle = 'Annotated Document'): DocumentData {
  const lines = rawText.split('\n');
  const root: OutlineNode = {
    id: 'root',
    label: '',
    title: docTitle,
    text: '',
    depth: 0,
    children: [],
  };

  const stack: { node: OutlineNode; depth: number }[] = [{ node: root, depth: 0 }];
  let preambleLines: string[] = [];
  let isPreamble = true;

  // Patterns for headers:
  // 1) Markdown: # Title (depth 1), ## (depth 2), ### (depth 3)
  // 2) Numbered: "1", "1.", "1.1", "2.2.(a)", "(a)", "Section 1"
  const mdRegex = /^(#{1,6})\s+(.+)$/;
  const numRegex = /^(\(?\d+(?:\.\d+)*(?:\.\([a-zA-Z0-9]+\))?\)|\([a-zA-Z0-9]+\))\s*(?:[-:.]\s*|\s+)(.+)$/;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trimEnd();
    const mdMatch = line.match(mdRegex);
    const numMatch = line.match(numRegex);

    if (mdMatch || numMatch) {
      isPreamble = false;
      let depth = 1;
      let label = '';
      let title = '';

      if (mdMatch) {
        depth = mdMatch[1].length;
        const remaining = mdMatch[2].trim();
        const innerNum = remaining.match(/^(\(?\d+(?:\.\d+)*(?:\.\([a-zA-Z0-9]+\))?\)|\([a-zA-Z0-9]+\))\s*(?:[-:.]\s*|\s+)(.+)$/);
        if (innerNum) {
          label = innerNum[1].replace(/[.)]$/, '');
          title = innerNum[2];
        } else {
          title = remaining;
          label = `${depth}`;
        }
      } else if (numMatch) {
        label = numMatch[1].replace(/[.)]$/, '');
        title = numMatch[2].trim();
        // infer depth from dot count or brackets
        const dots = (label.match(/\./g) || []).length;
        depth = dots + 1;
        if (label.includes('(')) {
          depth += 1;
        }
      }

      const newNode: OutlineNode = {
        id: generateNodeId(label),
        label,
        title,
        text: '',
        depth,
        children: [],
      };

      // Pop stack until parent depth is strictly less than target depth
      while (stack.length > 1 && stack[stack.length - 1].depth >= depth) {
        stack.pop();
      }

      const parentEntry = stack[stack.length - 1];
      parentEntry.node.children.push(newNode);
      stack.push({ node: newNode, depth });
    } else {
      if (isPreamble) {
        if (line.trim()) {
          preambleLines.push(line);
        }
      } else {
        // Append to current top node's text
        const current = stack[stack.length - 1].node;
        if (current.id !== 'root') {
          current.text = current.text ? `${current.text}\n${line}` : line;
        }
      }
    }
  }

  root.text = preambleLines.join('\n').trim() || 'seed';
  return { root: recomputeDepths(root, 0) };
}
