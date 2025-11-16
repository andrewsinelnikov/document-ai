import { useEffect, useState } from 'react';
import ContractCard from '../components/ContractCard';
import { api, type ContractTypeResponse } from '../api/api';
import { useNavigate } from 'react-router-dom';
import styles from './Home.module.css';

export default function Home() {
  const [contracts, setContracts] = useState<ContractTypeResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.getContractTypes()
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