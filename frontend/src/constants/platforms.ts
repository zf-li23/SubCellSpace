/** 平台配置 */
export interface PlatformDef {
  key: string
  label: string
  file: string
  icon: string
}

export const PLATFORMS: PlatformDef[] = [
  { key: 'cosmx',  label: 'CosMx',  file: 'cosmx.json',  icon: '🧬' },
  { key: 'xenium', label: 'Xenium', file: 'xenium.json', icon: '🔬' },
  { key: 'merfish',label: 'MERFISH',file: 'merfish.json',icon: '🧪' },
]
