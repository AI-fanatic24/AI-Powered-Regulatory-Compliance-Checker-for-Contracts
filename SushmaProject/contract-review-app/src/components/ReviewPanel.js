import React from 'react';

export default function ReviewPanel({ contract, review, darkColors }) {
  return (
    <section
      style={{
        backgroundColor: darkColors.cardBackground,
        padding: 20,
        borderRadius: 8,
        boxShadow: '0 0 10px rgba(0,0,0,0.7)',
      }}
    >
      <h2 style={{ marginBottom: 20 }}>
        Review Results for:{' '}
        <span style={{ color: darkColors.green }}>{contract.name}</span>
      </h2>

      <div style={{ marginBottom: 20 }}>
        <h3>Missing Clauses</h3>
        <ul>
          {review.missingClauses.map((clause, idx) => (
            <li key={idx}>{clause}</li>
          ))}
        </ul>
      </div>

      <div style={{ marginBottom: 20 }}>
        <h3>Risks</h3>
        <ul>
          {review.risks.map((risk, idx) => (
            <li key={idx} style={{ color: darkColors.red, fontWeight: '600' }}>
              {risk}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3>Recommendations</h3>
        <ul>
          {review.recommendations.map((rec, idx) => (
            <li key={idx}>{rec}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}