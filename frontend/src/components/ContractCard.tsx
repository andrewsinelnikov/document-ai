import type { ContractType } from '../types/contract';
import { Home, Briefcase, Lock, DollarSign } from 'lucide-react';

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
    <div 
      onClick={onClick}
      className="bg-white p-6 rounded-lg shadow-sm border-2 border-transparent hover:border-diia-blue transition-all cursor-pointer"
    >
      <Icon className="w-8 h-8 text-diia-blue mb-3" />
      <h3 className="text-lg font-semibold text-diia-dark">{type}</h3>
      <p className="text-sm text-diia-gray mt-1">Готово за 3–5 хвилин</p>
    </div>
  );
}