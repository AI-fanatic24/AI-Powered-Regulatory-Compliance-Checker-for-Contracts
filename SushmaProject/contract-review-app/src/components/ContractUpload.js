import React from 'react';

export default function ContractUpload({ onUpload, darkColors }) {
  const handleChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUpload(file);
      e.target.value = null; // reset input
    }
  };

  return (
    <section
      style={{
        backgroundColor: darkColors.cardBackground,
        padding: 20,
        borderRadius: 8,
        boxShadow: '0 0 10px rgba(0,0,0,0.7)',
      }}
    >
      <h2>Upload Contract</h2>
      <input
        type="file"
        onChange={handleChange}
        style={{
          backgroundColor: darkColors.buttonBackground,
          color: darkColors.textPrimary,
          border: 'none',
          padding: '10px 15px',
          borderRadius: 5,
          cursor: 'pointer',
        }}
      />
    </section>
  );
}