import { Shield } from 'lucide-react';

export default function Header() {
  return (
    <header className="text-center py-8">
      <div className="flex justify-center items-center gap-3 mb-2">
        <Shield className="w-10 h-10 text-diia-blue" />
        <h1 className="text-4xl font-bold text-diia-dark">Договір AI</h1>
      </div>
      <p className="text-diia-gray">Створіть юридичний договір за 5 хвилин без юриста</p>
    </header>
  );
}
