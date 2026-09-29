import { describe, it, expect } from 'vitest'
import { geoAccession, parsePmids } from '../pages/DataBrowser'

describe('geoAccession', () => {
  it('links merged CosMx ranges to the first GSM', () => {
    expect(geoAccession('GSM8529618-GSM8529620')).toBe('GSM8529618')
  })
  it('keeps plain accessions', () => {
    expect(geoAccession('GSE234713')).toBe('GSE234713')
  })
})

describe('parsePmids', () => {
  it('splits comma-separated lists', () => {
    expect(parsePmids('38168317, 39901013, 41390915')).toEqual(['38168317', '39901013', '41390915'])
  })
  it('drops float suffixes from CSV round-trips', () => {
    expect(parsePmids('37433806.0')).toEqual(['37433806'])
  })
  it('ignores empty and non-numeric values', () => {
    expect(parsePmids(null)).toEqual([])
    expect(parsePmids('2023/10/09')).toEqual([])
  })
})
