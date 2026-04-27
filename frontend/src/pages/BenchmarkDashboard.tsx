import React, { useEffect, useState } from 'react'
import { loadBenchmarkSummary, type BenchmarkSummary } from '../api'

export default function BenchmarkDashboard(){
  const [bench, setBench] = useState<BenchmarkSummary | null>(null)

  useEffect(() => {
    loadBenchmarkSummary().then((value) => setBench(value))
  }, [])

  return (
    <div className="container">
      <h2>Benchmark</h2>
      <div className="card">
        {bench ? <pre>{JSON.stringify(bench, null, 2)}</pre> : <div>Benchmark summary not found (check outputs/cosmx_benchmark_round)</div>}
      </div>
    </div>
  )
}
