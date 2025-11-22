import { useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { generate } from '../api/api';
import styles from './ContractFlow.module.css';
import { Loader2, ArrowLeft, Download, FileText } from 'lucide-react';
import type { ContractType, FormField, ContractResult } from '../types/contract';
// import { marked } from 'marked';


const fieldsMap: Record<ContractType, FormField[]> = {
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

// Мапа назв договорів
const contractTitles: Record<ContractType, string> = {
  rent_contract: 'Договір оренди житла',
  loan_contract: 'Договір позики',
  nda_contract: 'Угода про нерозголошення (NDA)',
  service_contract: 'Договір надання послуг',
};

export default function ContractFlow() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const contractType = (state as any)?.type as ContractType | undefined;

  // Редірект, якщо тип не переданий
  useEffect(() => {
    if (!contractType || !fieldsMap[contractType]) {
      navigate('/');
    }
  }, [contractType, navigate]);

  if (!contractType || !fieldsMap[contractType]) {
    return null;
  }

  const fields = fieldsMap[contractType];
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<ContractResult | null>(null);
  const [pdfBase64, setPdfBase64] = useState<string>('');
  const [error, setError] = useState('');

  const current = fields[step];

  // Валідація поточного поля
  const isCurrentValid = () => {
    if (!current.required) return true;
    const value = answers[current.id]?.toString().trim();
    return !!value;
  };

  const handleNext = () => {
    if (!isCurrentValid()) {
      setError('Це поле обов’язкове');
      return;
    }
    setError('');

    if (step === fields.length - 1) {
      handleGenerate();
    } else {
      setStep(prev => prev + 1);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError('');
    try {
      const res = await generate(contractType, answers);
      setResult(res);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Помилка генерації договору. Спробуйте ще раз.');
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    if (result?.content_pdf_base64) {
      setPdfBase64(result.content_pdf_base64);
    }
  }, [result]);

  const downloadPdf = () => {
    if (!pdfBase64 || !result) return;
    const link = document.createElement('a');
    link.href = `data:application/pdf;base64,${pdfBase64}`;
    link.download = `${result.title}.pdf`;
    link.click();
  };

  const downloadMarkdown = () => {
    if (!result) return;
    const blob = new Blob([result.content_markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${result.title || contractTitles[contractType]}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // === Результат ===
  if (result) {
    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <div className="flex justify-between items-center mb-8">
            <button onClick={() => navigate('/')} className={styles.backButton}>
              <ArrowLeft size={20} />
            </button>
            <h2 className={styles.title}>Договір готовий!</h2>
            <div className="w-8" />
          </div>

          {/* Прев'ю договору */}
          <div className={styles.previewWrapper}>
            {result.content_html ? (
              <div
                className={styles.contractPreview}
                dangerouslySetInnerHTML={{ __html: result.content_html }}
              />
            ) : (
              <div className="text-center py-12 text-gray-500">Завантаження вмісту...</div>
            )}
          </div>

          {/* Кнопки дій */}
          <div className="flex flex-wrap gap-4 justify-center mt-8">
            <button onClick={downloadPdf} className={styles.button}>
              <Download className="inline mr-2" size={18} />
              Завантажити PDF
            </button>

            <button onClick={downloadMarkdown} className={styles.buttonSecondary}>
              Завантажити .md
            </button>

            <button
              onClick={() => {
                setResult(null);
                setPdfBase64('');
                setStep(0);
                setAnswers({});
              }}
              className={styles.buttonOutline}
            >
              Новий договір
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
            <ArrowLeft size={20} />
          </button>
          <h2 className={styles.title}>{contractTitles[contractType]}</h2>
          <div className="w-8" />
        </div>

        {/* Прогрес */}
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

        {/* Поле вводу */}
        {current && (
          <div className="mt-8">
            <p className={styles.question}>{current.label}</p>

            {current.type === 'textarea' ? (
              <textarea
                className={styles.textarea}
                rows={6}
                value={answers[current.id] || ''}
                onChange={(e) => setAnswers({ ...answers, [current.id]: e.target.value })}
                placeholder="Введіть детальну відповідь..."
                autoFocus
              />
            ) : (
              <input
                type={current.type === 'date' ? 'date' : current.type === 'number' ? 'number' : 'text'}
                className={styles.input}
                value={answers[current.id] || ''}
                onChange={(e) => setAnswers({ ...answers, [current.id]: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && isCurrentValid() && handleNext()}
                placeholder="Ваша відповідь..."
                autoFocus
              />
            )}

            {error && <p className={styles.error}>{error}</p>}

            <div className="mt-8 flex justify-between">
              <button
                onClick={() => setStep(Math.max(0, step - 1))}
                disabled={step === 0}
                className={styles.buttonSecondary}
              >
                Назад
              </button>

              <button
                onClick={handleNext}
                disabled={generating || !isCurrentValid()}
                className={styles.button}
              >
                {generating ? (
                  <>Генерація <Loader2 className="animate-spin inline ml-2" /></>
                ) : step === fields.length - 1 ? (
                  'Згенерувати договір'
                ) : (
                  'Далі →'
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}