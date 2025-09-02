import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import ContractUpload from './components/ContractUpload';
import ContractList from './components/ContractList';
import ReviewPanel from './components/ReviewPanel';
import DataSources from './components/DataSources';
import Notifications from './components/Notifications';

const darkColors = {
  background: '#121212',
  cardBackground: '#1e1e1e',
  textPrimary: '#e0e0e0',
  textSecondary: '#a0a0a0',
  buttonBackground: '#3a3a3a',
  buttonHover: '#575757',
  border: '#333',
  red: '#ff6b6b',
  green: '#4caf50',
};

function App() {
  const [contracts, setContracts] = useState([]);
  const [selectedContract, setSelectedContract] = useState(null);
  const [reviewResult, setReviewResult] = useState(null);

  const handleUpload = (file) => {
    setContracts((prev) => [...prev, { id: Date.now(), name: file.name }]);
  };

  const reviewContract = (contract) => {
    setSelectedContract(contract);
    setReviewResult({
      missingClauses: ['Data Protection Clause', 'Breach Notification Clause'],
      risks: ['Non-compliance with GDPR Article 33'],
      recommendations: [
        'Add Data Protection Clause referencing GDPR requirements.',
        'Include Breach Notification Clause with 72-hour notification period.',
      ],
    });
  };

  return (
    <div
      style={{
        backgroundColor: darkColors.background,
        color: darkColors.textPrimary,
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      }}
    >
      <Navbar darkColors={darkColors} />

      <main
        style={{
          flex: 1,
          maxWidth: 1000,
          margin: '20px auto',
          padding: '0 20px',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          gap: 40,
        }}
      >
        <ContractUpload onUpload={handleUpload} darkColors={darkColors} />

        <ContractList
          contracts={contracts}
          onReview={reviewContract}
          darkColors={darkColors}
        />

        {selectedContract && reviewResult && (
          <ReviewPanel
            contract={selectedContract}
            review={reviewResult}
            darkColors={darkColors}
          />
        )}

        <DataSources darkColors={darkColors} />

        <Notifications darkColors={darkColors} />
      </main>

      <Footer darkColors={darkColors} />
    </div>
  );
}

export default App;