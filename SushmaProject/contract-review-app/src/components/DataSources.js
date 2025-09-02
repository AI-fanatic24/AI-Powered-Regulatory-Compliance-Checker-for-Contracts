import React from 'react';

export default function DataSources({ darkColors }) {
  return (
    <section
      style={{
        backgroundColor: darkColors.cardBackground,
        padding: 20,
        borderRadius: 8,
        boxShadow: '0 0 10px rgba(0,0,0,0.7)',
      }}
    >
      <h2>Data Source Integrations</h2>
      <p style={{ color: darkColors.textSecondary }}>
        Connect Google Sheets, Emails, and Public Websites for real-time updates.
      </p>
      {/* Future integration UI components */}
    </section>
  );
}