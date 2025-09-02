import React from 'react';

export default function Navbar({ darkColors }) {
  return (
    <nav
      style={{
        backgroundColor: darkColors.cardBackground,
        padding: '15px 30px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        color: darkColors.textPrimary,
      }}
    >
      <h1 style={{ margin: 0, fontSize: 24, fontWeight: '700' }}>
        Contract AI Compliance
      </h1>
      <ul
        style={{
          listStyle: 'none',
          display: 'flex',
          gap: 20,
          margin: 0,
          padding: 0,
          fontWeight: '600',
          fontSize: 16,
        }}
      >
        <li style={{ cursor: 'pointer' }}>Dashboard</li>
        <li style={{ cursor: 'pointer' }}>Contracts</li>
        <li style={{ cursor: 'pointer' }}>Settings</li>
      </ul>
    </nav>
  );
}