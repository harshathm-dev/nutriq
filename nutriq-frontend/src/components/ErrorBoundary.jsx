import React from 'react';
import { AlertCircle, RefreshCw, RotateCcw } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onRetry) {
      this.props.onRetry();
    }
  };

  render() {
    if (this.state.hasError) {
      const fallbackTitle = this.props.title || "Something went wrong while loading this page.";
      return (
        <div
          className="glass-panel"
          style={{
            padding: '48px 24px',
            textAlign: 'center',
            maxWidth: '620px',
            margin: '40px auto',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(15, 23, 42, 0.75))',
            borderRadius: 'var(--radius-lg)'
          }}
        >
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '16px',
              background: 'rgba(239, 68, 68, 0.2)',
              color: '#f87171',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto'
            }}
          >
            <AlertCircle size={28} />
          </div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '800', marginBottom: '8px', color: 'var(--text-primary)' }}>
            {fallbackTitle}
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '24px', lineHeight: '1.5', maxWidth: '480px', margin: '0 auto 24px auto' }}>
            {this.state.error?.message || "An unexpected rendering issue occurred. Please retry or refresh the page."}
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <button onClick={this.handleRetry} className="btn-primary" style={{ padding: '10px 20px', fontSize: '0.88rem' }}>
              <RotateCcw size={16} /> Try Again
            </button>
            <button onClick={() => window.location.reload()} className="btn-secondary" style={{ padding: '10px 20px', fontSize: '0.88rem' }}>
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
