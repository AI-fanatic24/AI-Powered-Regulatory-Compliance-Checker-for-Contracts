import React from 'react';

export default function Footer({ darkColors }) {
  return (
    <footer
      style={{
        backgroundColor: darkColors.cardBackground,
        padding: '15px 30px',
        textAlign: 'center',
        color: darkColors.textSecondary,
        fontSize: 14,
        boxShadow: '0 -2px 8px rgba(0,0,0,0.7)',
      }}
    >
      &copy; {new Date().getFullYear()} Contract AI Compliance. All rights reserved.
    </footer>
  );
}