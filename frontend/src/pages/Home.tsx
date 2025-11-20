// src/pages/Home.tsx — ФІНАЛЬНА ВЕРСІЯ (працює з новим бекендом)

import { useEffect, useState } from 'react';
import ContractCard from '../components/ContractCard';
import { getContractTypes } from '../api/api'; // ← ЗАМІНИВ api.getContractTypes на іменовану функцію
import { useNavigate } from 'react-router-dom';
import styles from './Home.module.css';

export default function Home() {
  const [contracts, setContracts] = useState<{ id: string; title: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getContractTypes() // ← тепер саме так
      .then(setContracts)
      .catch(() => alert('Помилка завантаження типів договорів'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className={styles.container}>Завантаження...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.grid}>
        {contracts.map((contract) => (
          <ContractCard
            key={contract.id}
            type={contract.title}
            onClick={() => navigate('/contract', { state: { type: contract.id } })}
          />
        ))}
      </div>
    </div>
  );
}