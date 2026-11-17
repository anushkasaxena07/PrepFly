import React from 'react';

export default class SuperAdminErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("SuperAdmin view crash intercepted:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          background: "#ffffff",
          border: "1px solid #fecaca",
          borderRadius: "16px",
          padding: "36px 24px",
          textAlign: "center",
          maxWidth: "600px",
          margin: "40px auto",
          boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.05)"
        }}>
          <div style={{ fontSize: "36px", marginBottom: "12px" }}>⚠️</div>
          <h3 style={{ fontSize: "18px", fontWeight: 800, color: "#991b1b", marginBottom: "8px" }}>
            View Error Occurred
          </h3>
          <p style={{ fontSize: "13px", color: "#64748b", lineHeight: 1.5, marginBottom: "20px" }}>
            An unexpected error occurred while rendering this section. Our system captured the incident without crashing your session.
          </p>
          {this.state.error && (
            <pre style={{
              background: "#fef2f2",
              color: "#b91c1c",
              padding: "12px",
              borderRadius: "8px",
              fontSize: "11px",
              textAlign: "left",
              overflowX: "auto",
              marginBottom: "20px",
              border: "1px solid #fee2e2"
            }}>
              {this.state.error.message || String(this.state.error)}
            </pre>
          )}
          <button
            onClick={this.handleReset}
            style={{
              background: "linear-gradient(135deg, #6d28d9, #7c3aed)",
              color: "#ffffff",
              border: "none",
              padding: "10px 20px",
              borderRadius: "8px",
              fontWeight: 700,
              fontSize: "13px",
              cursor: "pointer"
            }}
          >
            🔄 Reload Section
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
