import type { ContractType } from '../types/contract';
import { Home, Briefcase, Lock, DollarSign } from 'lucide-react';
import styles from './ContractCard.module.css';

const icons = {
  "Оренда квартири": Home,
  "Надання послуг (ФОП)": Briefcase,
  "NDA": Lock,
  "Позика": DollarSign,
};

interface Props {
  type: ContractType;
  onClick: () => void;
}

export default function ContractCard({ type, onClick }: Props) {
  const Icon = icons[type];
  return (
    <div className={styles.card} onClick={onClick}>
      <Icon className={styles.icon} />
      <h3 className={styles.title}>{type}</h3>
      <p className={styles.description}>Готово за 3–5 хвилин</p>
    </div>
  );
}