/** LabVision Hub 的视觉资产分类与标签建议 */
export const PICTURE_CATEGORY_KEYWORDS = [
  '实验流程',
  '仪器设备',
  '样品记录',
  '数据图表',
  '研究成果',
]

export const PICTURE_TAG_KEYWORDS = [
  '显微成像',
  '实验装置',
  '样品制备',
  '原始数据',
  '结果分析',
  '论文配图',
  '安全规范',
  '设备维护',
]

export const toSelectOptions = (keywords: string[]) =>
  keywords.map((keyword) => ({
    value: keyword,
    label: keyword,
  }))
