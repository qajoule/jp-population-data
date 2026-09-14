export type FigureMeta = {
  id: string;
  groupId: string;
  title: string;
  observation: string;
  notes: string[];
  transformation: string;
};

export type FigureGroupMeta = {
  id: string;
  title: string;
  observation: string;
  notes: string[];
  transformation: string;
};

const ageStructureNotes = [
  "縦の破線は観測方法が変わった年を示しています",
];

const youthCountNotes = [
  "縦の破線は観測方法が変わった年を示しています",
];

const youthPopulationNotes = [
  "縦の破線は観測方法が変わった年を示しています",
];

const vitalSuicideRateBySexNotes = [
  "対象: 人口動態統計（日本における日本人）",
  "人口の基準: 確定値・各歳",
];

export const figureGroupMetas: FigureGroupMeta[] = [
  {
    id: "vital-suicide-rate-by-sex",
    title: "年齢階級別の男女別自殺死亡率",
    observation: "年齢階級別の男女別自殺死亡率 (人口10万人あたりの自殺者数)",
    notes: vitalSuicideRateBySexNotes,
    transformation: "自殺死亡率（人口10万対） = 自殺者数 ÷ 人口 × 100,000",
  },
];

export const figureMetas: FigureMeta[] = [
  {
    id: "age-structure-persons",
    groupId: "age-structure-persons",
    title: "年齢 3 区分の人口",
    observation: "年齢3区分の人口推移",
    notes: ageStructureNotes,
    transformation: "年齢区分を集計し、人数と構成比を計算する",
  },
  {
    id: "age-structure-share",
    groupId: "age-structure-share",
    title: "年齢 3 区分の構成比",
    observation: "年齢3区分の人口構成比",
    notes: ageStructureNotes,
    transformation: "年齢区分を集計し、人数と構成比を計算する",
  },
  {
    id: "vital-counts",
    groupId: "vital-counts",
    title: "出生数と死亡数と自然増減",
    observation: "出生数、死亡数、自然増減の推移",
    notes: [],
    transformation: "自然増減 = 出生数 - 死亡数",
  },
  {
    id: "total-fertility-rate",
    groupId: "total-fertility-rate",
    title: "合計特殊出生率",
    observation: "合計特殊出生率の推移",
    notes: [],
    transformation: "加工なし",
  },
  {
    id: "suicide-count-by-age",
    groupId: "suicide-count-by-age",
    title: "年齢階級別の自殺者数",
    observation: "年齢階級別の自殺者数",
    notes: [],
    transformation: "加工なし",
  },
  {
    id: "suicide-rate-by-age",
    groupId: "suicide-rate-by-age",
    title: "年齢階級別の自殺死亡率",
    observation: "年齢階級別の自殺死亡率 (人口10万人あたりの自殺者数)",
    notes: [
      "人口の基準: 1995-2024年は確定値・各歳",
      "人口の基準: 2025年は概算値・5歳階級",
    ],
    transformation: "自殺死亡率（人口10万対） = 自殺者数 ÷ 人口 × 100,000",
  },
  {
    id: "youth-suicide-count",
    groupId: "youth-suicide-count",
    title: "0-19 歳の自殺者数",
    observation: "0-19歳の自殺者数",
    notes: youthCountNotes,
    transformation: "加工なし",
  },
  {
    id: "youth-population",
    groupId: "youth-population",
    title: "0-19 歳の人口",
    observation: "0-19歳の人口",
    notes: youthPopulationNotes,
    transformation: "年齢区分を集計する",
  },
  {
    id: "youth-suicide-rate",
    groupId: "youth-suicide-rate",
    title: "0-19 歳の自殺死亡率",
    observation: "0-19歳の自殺死亡率 (人口10万人あたりの自殺者数)",
    notes: [
      "縦の破線は観測方法が変わった年を示しています",
    ],
    transformation: "自殺死亡率（人口10万対） = 自殺者数 ÷ 人口 × 100,000",
  },
  {
    id: "vital-suicide-rate-0-19",
    groupId: "vital-suicide-rate-by-sex",
    title: "0-19 歳の男女別自殺死亡率",
    observation: "0-19歳の男女別自殺死亡率 (人口10万人あたりの自殺者数)",
    notes: vitalSuicideRateBySexNotes,
    transformation: "自殺死亡率（人口10万対） = 自殺者数 ÷ 人口 × 100,000",
  },
  {
    id: "vital-suicide-rate-20-29",
    groupId: "vital-suicide-rate-by-sex",
    title: "20-29 歳の男女別自殺死亡率",
    observation: "20-29歳の男女別自殺死亡率 (人口10万人あたりの自殺者数)",
    notes: [],
    transformation: "自殺死亡率（人口10万対） = 自殺者数 ÷ 人口 × 100,000",
  },
  {
    id: "vital-suicide-rate-30-39",
    groupId: "vital-suicide-rate-by-sex",
    title: "30-39 歳の男女別自殺死亡率",
    observation: "30-39歳の男女別自殺死亡率 (人口10万人あたりの自殺者数)",
    notes: [],
    transformation: "自殺死亡率（人口10万対） = 自殺者数 ÷ 人口 × 100,000",
  },
  {
    id: "vital-suicide-rate-40-49",
    groupId: "vital-suicide-rate-by-sex",
    title: "40-49 歳の男女別自殺死亡率",
    observation: "40-49歳の男女別自殺死亡率 (人口10万人あたりの自殺者数)",
    notes: [],
    transformation: "自殺死亡率（人口10万対） = 自殺者数 ÷ 人口 × 100,000",
  },
  {
    id: "vital-suicide-rate-50-59",
    groupId: "vital-suicide-rate-by-sex",
    title: "50-59 歳の男女別自殺死亡率",
    observation: "50-59歳の男女別自殺死亡率 (人口10万人あたりの自殺者数)",
    notes: [],
    transformation: "自殺死亡率（人口10万対） = 自殺者数 ÷ 人口 × 100,000",
  },
  {
    id: "vital-suicide-rate-60-plus",
    groupId: "vital-suicide-rate-by-sex",
    title: "60 歳以上の男女別自殺死亡率",
    observation: "60歳以上の男女別自殺死亡率 (人口10万人あたりの自殺者数)",
    notes: [],
    transformation: "自殺死亡率（人口10万対） = 自殺者数 ÷ 人口 × 100,000",
  },
];

export const seriesStyles = {
  "出生": { sourceColor: "#2a78d6", lineStyle: "solid" },
  "死亡": { sourceColor: "#eb6834", lineStyle: "dash" },
  "自然増減": { sourceColor: "#4b5563", lineStyle: "short-dash" },
  "合計特殊出生率": { sourceColor: "#4b5563", lineStyle: "solid" },
  "0-14歳": { sourceColor: "#2a78d6", lineStyle: "solid" },
  "15-64歳": { sourceColor: "#eb6834", lineStyle: "dash" },
  "65歳以上": { sourceColor: "#008300", lineStyle: "dot" },
  "合計": { sourceColor: "#4b5563", lineStyle: "double-dot" },
  "0-19歳": { sourceColor: "#2a78d6", lineStyle: "solid" },
  "20-29歳": { sourceColor: "#eb6834", lineStyle: "dash" },
  "30-39歳": { sourceColor: "#1baf7a", lineStyle: "dot" },
  "40-49歳": { sourceColor: "#eda100", lineStyle: "long-dash" },
  "50-59歳": { sourceColor: "#e87ba4", lineStyle: "dash-dot" },
  "60歳以上": { sourceColor: "#008300", lineStyle: "short-dash" },
  "男": { sourceColor: "#2a78d6", lineStyle: "solid" },
  "女": { sourceColor: "#e87ba4", lineStyle: "dash" },
} as const;

// This is the complete set of series each generated figure is expected to render.
// Keep it next to seriesStyles so the pre-build check can catch an incomplete style table.
export const renderedSeriesByFigure = {
  "age-structure-persons": ["0-14歳", "15-64歳", "65歳以上"],
  "age-structure-share": ["0-14歳", "15-64歳", "65歳以上"],
  "vital-counts": ["出生", "死亡", "自然増減"],
  "total-fertility-rate": ["合計特殊出生率"],
  "suicide-count-by-age": ["合計", "0-19歳", "20-29歳", "30-39歳", "40-49歳", "50-59歳", "60歳以上"],
  "suicide-rate-by-age": ["合計", "0-19歳", "20-29歳", "30-39歳", "40-49歳", "50-59歳", "60歳以上"],
  "youth-suicide-count": ["0-19歳"],
  "youth-population": ["0-19歳"],
  "youth-suicide-rate": ["0-19歳"],
  "vital-suicide-rate-0-19": ["男", "女"],
  "vital-suicide-rate-20-29": ["男", "女"],
  "vital-suicide-rate-30-39": ["男", "女"],
  "vital-suicide-rate-40-49": ["男", "女"],
  "vital-suicide-rate-50-59": ["男", "女"],
  "vital-suicide-rate-60-plus": ["男", "女"],
} as const;

function namesDiffer(left: readonly string[], right: readonly string[]) {
  return left.length !== right.length || left.some((name) => !right.includes(name));
}

export function assertFigureSeriesDeclaration(figureId: string, seriesNames: readonly string[]) {
  const expected = renderedSeriesByFigure[figureId as keyof typeof renderedSeriesByFigure];
  if (!expected) throw new Error(`系列宣言に図がありません: ${figureId}`);
  const actual = [...new Set(seriesNames)];
  if (namesDiffer(actual, expected)) {
    throw new Error(`${figureId}: 描画系列が宣言と一致しません (実際: ${actual.join(", ")}; 宣言: ${expected.join(", ")})`);
  }
  const missing = actual.filter((name) => !(name in seriesStyles));
  if (missing.length) throw new Error(`${figureId}: seriesStyles に系列がありません: ${missing.join(", ")}`);
}

export function assertRenderedFigureCoverage(figureIds: readonly string[]) {
  const expectedIds = Object.keys(renderedSeriesByFigure);
  if (namesDiffer(figureIds, expectedIds)) {
    throw new Error(`図の系列宣言が不一致です (描画: ${figureIds.join(", ")}; 宣言: ${expectedIds.join(", ")})`);
  }
  const renderedSeries = [...new Set(Object.values(renderedSeriesByFigure).flat())];
  const missing = renderedSeries.filter((name) => !(name in seriesStyles));
  if (missing.length) throw new Error(`seriesStyles 網羅検査が失敗しました: ${missing.length}/${renderedSeries.length} 系列が不足 (${missing.join(", ")})`);
  return { figureCount: expectedIds.length, seriesCount: renderedSeries.length };
}
