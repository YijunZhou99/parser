export interface OutlineNode {
  id: string;
  label: string;
  title: string;
  text: string;
  depth: number;
  children: OutlineNode[];
}

export interface DocumentData {
  root: OutlineNode;
}

export type DropPosition = 'before' | 'after' | 'inside';
