import ContractCard from '../components/ContractCard';
import type { ContractType } from '../types/contract';
import { useNavigate } from 'react-router-dom';

export default function Home() {
  const navigate = useNavigate();

  const contracts: ContractType[] = [
    "Оренда квартири",
    "Надання послуг (ФОП)",
    "NDA",
    "Позика"
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="grid md:grid-cols-2 gap-6">
        {contracts.map(type => (
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
