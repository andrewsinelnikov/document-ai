// src/pages/ContractFlow.tsx — ФІНАЛЬНА ВЕРСІЯ ДЛЯ AI-БЕКЕНДУ
import { useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { generate } from '../api/api';
import styles from './ContractFlow.module.css';
import { Loader2, ArrowLeft } from 'lucide-react';

export default function ContractFlow() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const contractType = (state as any)?.type;
  if (!contractType) {
    navigate('/');
    return null;
  }

  // === Динамічні поля (можна винести в окремий файл) ===
  const fieldsMap: Record<string, { id: string; label: string; type: string; required?: boolean }[]> = {
    rent_contract: [
      { id: "landlord_name", label: "ПІБ орендодавця", type: "text", required: true },
      { id: "landlord_passport", label: "Паспорт орендодавця", type: "text", required: true },
      { id: "landlord_phone", label: "Телефон орендодавця", type: "text", required: true },
      { id: "tenant_name", label: "ПІБ орендаря", type: "text", required: true },
      { id: "tenant_passport", label: "Паспорт орендаря", type: "text", required: true },
      { id: "tenant_phone", label: "Телефон орендаря", type: "text", required: true },
      { id: "property_address", label: "Адреса квартири", type: "text", required: true },
      { id: "rent_amount", label: "Орендна плата (грн/місяць)", type: "number", required: true },
      { id: "deposit_amount", label: "Застава (грн)", type: "number" },
      { id: "start_date", label: "Дата початку оренди", type: "date", required: true },
      { id: "end_date", label: "Дата закінчення оренди", type: "date", required: true },
    ],
    loan_contract: [
      { id: "lender_name", label: "ПІБ позикодавця", type: "text", required: true },
      { id: "lender_passport", label: "Паспорт позикодавця", type: "text", required: true },
      { id: "lender_phone", label: "Телефон позикодавця", type: "text", required: true },
      { id: "borrower_name", label: "ПІБ позичальника", type: "text", required: true },
      { id: "borrower_passport", label: "Паспорт позичальника", type: "text", required: true },
      { id: "borrower_phone", label: "Телефон позичальника", type: "text", required: true },
      { id: "loan_amount", label: "Сума позики (грн)", type: "number", required: true },
      { id: "interest_rate", label: "Відсотки річних (0 = безвідсоткова)", type: "number" },
      { id: "return_date", label: "Дата повернення", type: "date", required: true },
    ],
    nda_contract: [
      { id: "disclosing_party_name", label: "Розкриваюча сторона (ПІБ/компанія)", type: "text", required: true },
      { id: "receiving_party_name", label: "Отримуюча сторона (ПІБ/компанія)", type: "text", required: true },
      { id: "purpose", label: "Мета передачі інформації", type: "textarea", required: true },
      { id: "confidential_info_description", label: "Що саме є конфіденційним", type: "textarea", required: true },
      { id: "duration_years", label: "Строк дії (років)", type: "number" },
      { id: "penalty_amount", label: "Штраф за порушення (грн)", type: "number", required: true },
    ],
    service_contract: [
      { id: "provider_name", label: "ПІБ Виконавця (ФОП)", type: "text", required: true },
      { id: "provider_fop_number", label: "ЄДРПОУ/Реєстр. номер ФОП", type: "text", required: true },
      { id: "client_name", label: "ПІБ Замовника (ФОП)", type: "text", required: true },
      { id: "client_fop_number", label: "ЄДРПОУ/Реєстр. номер Замовника", type: "text", required: true },
      { id: "service_description", label: "Опис послуг", type: "textarea", required: true },
      { id: "service_amount", label: "Вартість послуг (грн)", type: "number", required: true },
      { id: "payment_term", label: "Термін оплати (днів після акту)", type: "number", required: true },
    ],
  };

  const fields = fieldsMap[contractType] || [];
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const current = fields[step];

  const handleNext = () => {
    if (!current) return;
    if (current.required && !answers[current.id]?.toString().trim()) {
      setError('Це поле обов’язкове');
      return;
    }
    setError('');
    if (step === fields.length - 1) {
      handleGenerate();
    } else {
      setStep(step + 1);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError('');
    try {
      const res = await generate(contractType, answers);
      setResult(res);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Помилка генерації договору');
    } finally {
      setGenerating(false);
    }
  };

  // === Рендер результату ===
  if (result) {
    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <div className="flex justify-between items-center mb-6">
            <button onClick={() => navigate('/')} className={styles.backButton}>
              <ArrowLeft />
            </button>
            <h2 className={styles.title}>Готово!</h2>
          </div>

          <div className="bg-gray-50 p-6 rounded-lg mb-6 max-h-96 overflow-y-auto">
            <pre className="whitespace-pre-wrap text-sm font-sans">{result.content_markdown}</pre>
          </div>

          <div className="flex gap-4">
            {result.content_pdf_base64 && (
              <button
                onClick={() => {
                  const link = document.createElement('a');
                  link.href = `data:application/pdf;base64,${result.content_pdf_base64}`;
                  link.download = `${result.title || 'Договір'}.pdf`;
                  link.click();
                }}
                className={styles.button}
              >
                Завантажити PDF
              </button>
            )}
            <button
              onClick={() => {
                const blob = new Blob([result.content_markdown], { type: 'text/markdown' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${result.title || 'Договір'}.md`;
                a.click();
              }}
              className={styles.button}
            >
              Завантажити .md
            </button>
          </div>
        </div>
      </div>
    );
  }

  // === Форма ===
  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className="flex justify-between items-center mb-6">
          <button onClick={() => navigate('/')} className={styles.backButton}>
            <ArrowLeft />
          </button>
          <h2 className={styles.title}>
            {contractType === 'rent_contract' && 'Договір оренди'}
            {contractType === 'loan_contract' && 'Договір позики'}
            {contractType === 'nda_contract' && 'NDA'}
            {contractType === 'service_contract' && 'Договір послуг'}
          </h2>
        </div>

        <div className={styles.progress}>
          <div className={styles.progressText}>
            Питання {step + 1} з {fields.length}
          </div>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${((step + 1) / fields.length) * 100}%` }}
            />
          </div>
        </div>

        {current && (
          <>
            <p className={styles.question}>{current.label}</p>

            {current.type === 'textarea' ? (
              <textarea
                className={styles.input}
                rows={5}
                value={answers[current.id] || ''}
                onChange={(e) => setAnswers({ ...answers, [current.id]: e.target.value })}
                placeholder="Ваша відповідь..."
              />
            ) : (
              <input
                type={current.type === 'number' ? 'number' : current.type === 'date' ? 'date' : 'text'}
                className={styles.input}
                value={answers[current.id] || ''}
                onChange={(e) => setAnswers({ ...answers, [current.id]: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && handleNext()}
                placeholder="Введіть відповідь"
              />
            )}

            {error && <p className={styles.error}>{error}</p>}

            <button
              onClick={handleNext}
              disabled={generating}
              className={styles.button}
            >
              {generating ? (
                <>Генерація <Loader2 className="animate-spin inline ml-2" /></>
              ) : step === fields.length - 1 ? (
                'Згенерувати договір'
              ) : (
                'Далі'
              )}
            </button>
          </>
        )}
      </div>
    </div>
  );
}