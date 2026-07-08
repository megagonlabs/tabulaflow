export type ViewKind = "map" | "chart" | "data" | "query" | "graph";
export type PaneSource = "manual";
export type ColumnRole = "text" | "number" | "bool" | "media";

export interface PaneCard {
  id: string;
  label: string | null;
  views: ViewKind[];
}

export interface PaneTurn {
  id?: number;
  title: string;
  cards: PaneCard[];
  user?: string;
  assistant?: string;
  source?: PaneSource;
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

export interface QueryData {
  sql: string;
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
  query?: QueryData;
  map?: MapData;
  graph?: GraphData;
  datasets?: Record<string, DatasetData>;
}

export interface ViewHandle {
  afterVisible?: () => void;
  afterHidden?: () => void;
  destroy?: () => void;
}

export interface ViewCacheEntry {
  node: HTMLElement;
  handle: ViewHandle | null;
  data: CardData | null;
  kind: ViewKind;
}

declare global {
  interface Window {
    Tabulator?: any;
    maplibregl?: any;
    vegaEmbed?: any;
    cytoscape?: any;
  }

  interface HTMLElement {
    _tfViewEntry?: ViewCacheEntry;
    _tfCy?: any;
  }
}
