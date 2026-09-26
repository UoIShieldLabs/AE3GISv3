/** A series on a shared x axis (null = no sample at that x). */
export interface ChartSeries {
  key: string;
  label: string;
  /** Categorical slot (--chart-N), 1-based, fixed by the entity (never by rank). */
  slot: number;
  dash?: boolean;
  values: (number | null)[];
}

export interface ChartData {
  x: number[];
  series: ChartSeries[];
}
