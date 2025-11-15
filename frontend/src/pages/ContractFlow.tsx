import { useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import type { ContractType } from '../types/contract';
import styles from './ContractFlow.module.css';

const questions: Record<ContractType, string[]> = {
  'Оренда квартири': [
    'Адреса квартири?',
    'ПІБ орендодавця?',
    'ПІБ орендаря?',
    'Термін оренди (місяців)?',
    'Місячна плата (грн)?',
  ],
  'Надання послуг (ФОП)': [
    'Назва послуги?',
    'ПІБ замовника?',
    'ПІБ виконавця?',
    'Вартість послуги (грн)?',
  ],
  'NDA': ['ПІБ сторони 1?', 'ПІБ сторони 2?', 'Термін дії угоди (місяців)?'],
  'Позика': [
    'Сума позики (грн)?',
    'ПІБ позичальника?',
    'ПІБ позикодавця?',
    'Термін повернення (місяців)?',
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
    <div className={styles.container}>
      <div className={styles.card}>
        <h2 className={styles.title}>{type}</h2>
        <div className={styles.progress}>
          <div className={styles.progressText}>
            Питання {step + 1} з {questions[type].length}
          </div>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${((step + 1) / questions[type].length) * 100}%` }}
            />
          </div>
        </div>
        {currentQuestion && (
          <div>
            <p className={styles.question}>{currentQuestion}</p>
            <input
              type="text"
              className={styles.input}
              placeholder="Ваша відповідь..."
              onKeyDown={(e) => e.key === 'Enter' && handleAnswer(e.currentTarget.value)}
            />
            <button
              onClick={() => handleAnswer((document.querySelector('input') as HTMLInputElement).value)}
              className={styles.button}
            >
              Далі
            </button>
          </div>
        )}
      </div>
    </div>
  );
}