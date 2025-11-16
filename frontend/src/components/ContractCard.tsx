// import type { ContractType } from '../types/contract';
import { Home, Briefcase, Lock, DollarSign, FileText } from 'lucide-react';
import styles from './ContractCard.module.css';

// const icons = {
//   "Оренда квартири": Home,
//   "Надання послуг (ФОП)": Briefcase,
//   "NDA": Lock,
//   "Позика": DollarSign,
// };

const icons: Record<string, any> = {
  "Оренда квартири": Home,
  "Надання послуг (ФОП)": Briefcase,
  "NDA": Lock,
  "Позика": DollarSign,
  "Договір оренди квартири": Home,       
  "Договір позики": DollarSign,          
  "НДА": Lock,
  "Договір надання послуг": Briefcase,
};

interface Props {
  type: string; 
  onClick: () => void;
}

export default function ContractCard({ type, onClick }: Props) {
  // const Icon = icons[type];
  const Icon = icons[type] || FileText;
  return (
    <div className={styles.card} onClick={onClick}>
      <Icon className={styles.icon} />
      <h3 className={styles.title}>{type}</h3>
      <p className={styles.description}>Готово за 3–5 хвилин</p>
    </div>
  );
}