import React from 'react';

export default function ContractList({ contracts, onReview, darkColors }) {
  if (contracts.length === 0) {
    return null;
  }

  return (
    <section
      style={{
        backgroundColor: darkColors.cardBackground,
        padding: 20,
        borderRadius: 8,
        boxShadow: '0 0 10px rgba(0,0,0,0.7)',
      }}
    >
      <h2>Contracts</h2>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 100px',
          gap: 10,
          marginTop: 10,
        }}
      >
        {contracts.map((contract) => (
          <React.Fragment key={contract.id}>
            <div
              style={{
                backgroundColor: darkColors.background,
                padding: 12,
                borderRadius: 6,
                border: `1px solid ${darkColors.border}`,
                display: 'flex',
                alignItems: 'center',
                color: darkColors.textSecondary,
                fontWeight: '600',
                overflowWrap: 'break-word',
              }}
            >
              {contract.name}
            </div>
            <button
              onClick={() => onReview(contract)}
              style={{
                backgroundColor: darkColors.buttonBackground,
                color: darkColors.textPrimary,
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: '600',
                transition: 'background-color 0.3s',
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.backgroundColor = darkColors.buttonHover)
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.backgroundColor = darkColors.buttonBackground)
              }
            >
              Review
            </button>
          </React.Fragment>
        ))}
      </div>
    </section>
  );
}