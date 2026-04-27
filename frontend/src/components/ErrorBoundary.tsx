import React, { Component, type ReactNode } from 'react'

type ErrorBoundaryProps = {
  children: ReactNode
  fallback?: ReactNode
}

type ErrorBoundaryState = {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="error-boundary">
          <div className="error-boundary-icon">⚠️</div>
          <h3>Something went wrong</h3>
          <p className="error-boundary-message">
            {this.state.error?.message ?? 'An unexpected error occurred.'}
          </p>
          <button className="error-boundary-retry" onClick={this.handleReset}>
            Try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}