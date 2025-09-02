import React from 'react';

export default function Notifications({ darkColors }) {
  return (
    <section
      style={{
        backgroundColor: darkColors.cardBackground,
        padding: 20,
        borderRadius: 8,
        boxShadow: '0 0 10px rgba(0,0,0,0.7)',
      }}
    >
      <h2>Notifications</h2>
      <p style={{ color: darkColors.textSecondary }}>No new notifications.</p>
      {/* Future notifications UI */}
    </section>
  );
}