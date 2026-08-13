export type ViewKind = "map" | "chart" | "data" | "query" | "graph";
export type PaneSource = "manual";
export type ColumnRole = "text" | "number" | "bool" | "media";

export interface PaneCard {
  id: string;
  label: string | null;
  views: ViewKind[];
}

export interface PaneControlChoice {
  id: string;
  label: string;
}

export interface PaneChoiceControl {
  kind: "choice";
  id: string;
  label: string;
  choices: PaneControlChoice[];
}

export interface PaneNumberControl {
  kind: "number";
  id: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  unit: string | null;
}

export type PaneControl = PaneChoiceControl | PaneNumberControl;

export interface PanePanel {
  controls: PaneControl[];
  default_selection: Record<string, string | number | boolean>;
}

export interface PaneTurn {
  id?: number;
  title: string;
  cards: PaneCard[];
  user?: string;
  assistant?: string;
  assistantCodeBlocks?: CodeData[];
  source?: PaneSource;
  panel?: PanePanel;
}

export interface ColumnDesc {
  title: string;
  field: string;
  role: ColumnRole;
}

export interface TableData {
  columns: ColumnDesc[];
  hasMedia?: boolean;
  maxHeight?: number | null;
  displayCap?: number;
  meta?: string;
  numRows?: number;
  numCols?: number;
  truncatedRows?: number;
  maxRows?: number;
}

export interface DatasetData {
  rows: Record<string, unknown>[];
  columns?: ColumnDesc[];
}

export interface ChartData {
  spec: Record<string, unknown>;
  renderer: string;
  wrapClass: string;
}

export interface CodeData {
  code: string;
  lexer: string;
  language: string;
  html: string;
}

export interface MapData {
  provider: string;
  layers: Record<string, unknown>[];
  view?: Record<string, unknown>;
}

export interface GraphData {
  layout: string;
  elements: Record<string, Record<string, unknown>[]>;
  meta?: Record<string, unknown>;
}

export interface CardData {
  table?: TableData;
  dataset?: DatasetData;
  chart?: ChartData;
  query?: CodeData;
  map?: MapData;
  graph?: GraphData;
  datasets?: Record<string, DatasetData>;
}

export interface ViewHandle {
  requires?: { width?: boolean; height?: boolean };
  mount?: () => void;
  resize?: () => void;
  destroy?: () => void;
}

export interface ViewCacheEntry {
  node: HTMLElement;
  handle: ViewHandle | null;
  data: CardData | null;
  kind: ViewKind;
  gated?: boolean;
  mounted?: boolean;
  observer?: ResizeObserver | null;
  gateFrame?: number | null;
}

declare global {
  interface Window {
    Tabulator?: any;
    katex?: any;
    markdownit?: any;
    texmath?: any;
    maplibregl?: any;
    vegaEmbed?: any;
    cytoscape?: any;
  }

  interface HTMLElement {
    _tfViewEntry?: ViewCacheEntry;
    _tfCy?: any;
  }
}
