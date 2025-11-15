import ContractCard from '../components/ContractCard';
import type { ContractType } from '../types/contract';
import { useNavigate } from 'react-router-dom';
import styles from './Home.module.css';

export default function Home() {
  const navigate = useNavigate();
  const contracts: ContractType[] = [
    'Оренда квартири',
    'Надання послуг (ФОП)',
    'NDA',
    'Позика',
  ];

  return (
    <div className={styles.container}>
      <div className={styles.grid}>
        {contracts.map((type) => (
          <ContractCard
            key={type}
            type={type}
            onClick={() => navigate('/contract', { state: { type } })}
          />
        ))}
      </div>
    </div>
  );
}