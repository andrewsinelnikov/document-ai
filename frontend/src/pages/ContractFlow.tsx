import { useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import type { ContractType } from '../types/contract';

const questions: Record<ContractType, string[]> = {
  "Оренда квартири": [
    "Адреса квартири?",
    "ПІБ орендодавця?",
    "ПІБ орендаря?",
    "Термін оренди (місяців)?",
    "Місячна плата (грн)?",
  ],
  "Надання послуг (ФОП)": [
    "Назва послуги?",
    "ПІБ замовника?",
    "ПІБ виконавця?",
    "Вартість послуги (грн)?",
  ],
  "NDA": [
    "ПІБ сторони 1?",
    "ПІБ сторони 2?",
    "Термін дії угоди (місяців)?",
  ],
  "Позика": [
    "Сума позики (грн)?",
    "ПІБ позичальника?",
    "ПІБ позикодавця?",
    "Термін повернення (місяців)?",
  ],
};

export default function ContractFlow() {
  const { state } = useLocation();
  const { type } = (state || {}) as { type: ContractType };
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<string[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    if (!type || !questions[type]) {
      alert('Невалідний тип договору!');
      navigate('/');
    }
  }, [type, navigate]);

  if (!type || !questions[type]) return null;

  const currentQuestion = questions[type][step];

  const handleAnswer = (answer: string) => {
    const newAnswers = [...answers, answer];
    setAnswers(newAnswers);
    if (step < questions[type].length - 1) {
      setStep(step + 1);
    } else {
      // TODO: надіслати на бекенд
      alert(`Договір "${type}" згенеровано!`);
      navigate('/');
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-2xl font-bold text-diia-dark mb-4">{type}</h2>
        <div className="mb-6">
          <div className="text-sm text-diia-gray">
            Питання {step + 1} з {questions[type].length}
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
            <div
              className="bg-diia-blue h-2 rounded-full transition-all"
              style={{ width: `${((step + 1) / questions[type].length) * 100}%` }}
            />
          </div>
        </div>

        {currentQuestion && (
          <div>
            <p className="text-lg font-medium text-diia-dark mb-4">{currentQuestion}</p>
            <input
              type="text"
              className="w-full p-3 border border-gray-300 rounded-lg focus:border-diia-blue focus:outline-none"
              placeholder="Ваша відповідь..."
              onKeyDown={(e) => e.key === 'Enter' && handleAnswer(e.currentTarget.value)}
            />
            <button
              onClick={() => handleAnswer((document.querySelector('input') as HTMLInputElement).value)}
              className="mt-4 w-full bg-diia-blue text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
            >
              Далі
            </button>
          </div>
        )}
      </div>
    </div>
  );
}