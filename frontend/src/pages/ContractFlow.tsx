import { useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import { api, type ContractField } from '../api/api';
import styles from './ContractFlow.module.css';
import { Loader2, ArrowLeft, Check } from 'lucide-react';
import validator from 'validator';  
import { jsPDF } from 'jspdf';

export default function ContractFlow() {
  const { state } = useLocation();
  const { type } = (state || {}) as { type: string };
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const [template, setTemplate] = useState<any>(null);
  const [fields, setFields] = useState<ContractField[]>([]);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});  // Змінили на any для чисел/дат
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatedContract, setGeneratedContract] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverValidated, setServerValidated] = useState(false);  // Флаг повної валідації

  useEffect(() => {
    if (!type) {
      navigate('/');
      return;
    }

    api.getTemplate(type)
      .then((tmpl) => {
        setTemplate(tmpl);
        const visibleFields = tmpl.fields.filter((f: ContractField) => !f.conditional);
        setFields(visibleFields);
      })
      .catch(() => {
        alert('Шаблон не знайдено');
        navigate('/');
      })
      .finally(() => setLoading(false));
  }, [type, navigate]);

  const currentField = fields[step];
  const progress = ((step + 1) / fields.length) * 100;

  const validateField = (field: ContractField, value: any): string | null => {
    const validation = field.validation || {};

    if (field.required && (value == null || value.toString().trim() === '')) {
      return `${field.label} є обов’язковим`;
    }

    if (field.type === 'text' || field.type === 'textarea') {
      if (validation.min_length && value.length < validation.min_length) {
        return `Мінімум ${validation.min_length} символів`;
      }
      if (validation.max_length && value.length > validation.max_length) {
        return `Максимум ${validation.max_length} символів`;
      }
      if (validation.pattern && !new RegExp(validation.pattern).test(value)) {
        return 'Невірний формат';
      }
    }

    if (field.type === 'number') {
      const num = Number(value);
      if (isNaN(num)) return 'Повинно бути числом';
      if (validation.min && num < validation.min) return `Мінімум ${validation.min}`;
      if (validation.max && num > validation.max) return `Максимум ${validation.max}`;
    }

    if (field.type === 'email') {
      if (!validator.isEmail(value)) return 'Невірний email';
    }

    if (field.type === 'phone') {
      if (!validator.isMobilePhone(value, 'uk-UA')) return 'Невірний номер телефону';
    }

    if (field.type === 'date') {
      const date = new Date(value);
      if (isNaN(date.getTime())) return 'Невірна дата';
      if (validation.future_date && date <= new Date()) return 'Дата повинна бути у майбутньому';
    }

    return null;
  };

  const handleInputChange = (value: string) => {
    let formattedValue: any = value;
    if (currentField.type === 'number') {
      formattedValue = value ? Number(value) : null;
    } else if (currentField.type === 'date') {
      formattedValue = value ? new Date(value).toISOString().split('T')[0] : null;
    }

    setAnswers({ ...answers, [currentField.id]: formattedValue });
    const error = validateField(currentField, formattedValue);
    setErrors({ ...errors, [currentField.id]: error || '' });
  };

  const handleNext = async () => {
    if (!currentField) return;

    const value = answers[currentField.id];
    const clientError = validateField(currentField, value);

    if (clientError) {
      setErrors({ ...errors, [currentField.id]: clientError });
      inputRef.current?.focus();
      return;  // Не переходити далі
    }

    // Опціонально: бекенд-валідація для цього поля (якщо потрібно)
    // const partialData = { [currentField.id]: value };
    // const validation = await api.validate(type, partialData);
    // if (!validation.valid) {
    //   setErrors({ ...errors, [currentField.id]: validation.errors[0]?.message || '' });
    //   return;
    // }

    if (step === fields.length - 1) {
      // Повна валідація перед генерацією
      await handleGenerate();
    } else {
      setStep(step + 1);
      setServerValidated(false);  // Скидання для нової генерації
    }
  };

  const handleGenerate = async () => {
    if (serverValidated) return;  // Уникаємо повторів

    setGenerating(true);
    const formattedAnswers: Record<string, any> = { ...answers };

    // Клієнтська перевірка всіх полів
    const allErrors: Record<string, string> = {};
    fields.forEach((field) => {
      const error = validateField(field, formattedAnswers[field.id]);
      if (error) allErrors[field.id] = error;
    });

    if (Object.keys(allErrors).length > 0) {
      setErrors(allErrors);
      setGenerating(false);
      alert('Виправте помилки в попередніх полях');
      return;
    }

    // Бекенд-валідація
    try {
      const validation = await api.validate(type, formattedAnswers);
      if (!validation.valid) {
        const errMap: Record<string, string> = {};
        validation.errors.forEach((e: any) => {
          errMap[e.field] = e.message;
        });
        setErrors(errMap);
        setGenerating(false);
        alert('Виправте помилки в формі');
        return;
      }

      // Генерація, якщо все OK
      const result = await api.generate(type, formattedAnswers);
      setGeneratedContract(result.content);
      setServerValidated(true);
    } catch (err: any) {
      alert(err.message || 'Помилка генерації');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <Loader2 className="animate-spin mx-auto" />
          <p className="text-center mt-2">Завантаження шаблону...</p>
        </div>
      </div>
    );
  }

  if (generatedContract) {
    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <div className="flex items-center justify-between mb-4">
            <h2 className={styles.title}>Договір згенеровано!</h2>
            <button onClick={() => navigate('/')} className={styles.backButton}>
              <ArrowLeft size={20} />
            </button>
          </div>
          <div className={styles.contractPreview}>
            <pre className="whitespace-pre-wrap font-sans text-sm">{generatedContract}</pre>
          </div>
          {/* <button
            onClick={() => {
              const blob = new Blob([generatedContract], { type: 'text/markdown' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `${template.title}.md`;
              a.click();
            }}
            className={styles.button}
          >
            Завантажити .md
          </button> */}
          
          <button
            onClick={() => {
              const doc = new jsPDF();
              doc.setFont('helvetica');
              doc.setFontSize(12);
              
              // Простий перенос тексту
              const splitText = doc.splitTextToSize(generatedContract, 180);
              doc.text(splitText, 15, 20);
              
              // Дисклеймер
              doc.setFontSize(10);
              doc.text(
                "УВАГА: Цей документ згенеровано автоматично на основі типового шаблону. " +
                "Сервіс не надає юридичних консультацій. Рекомендуємо перевірити договір у юриста при наявності особливих умов.",
                15, 280
              );

              doc.save(`${template?.title || 'Договір'}.pdf`);
            }}
            className={styles.button}
          >
            Завантажити PDF
          </button>

        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className="flex items-center justify-between mb-4">
          <h2 className={styles.title}>{template?.title}</h2>
          <button onClick={() => navigate('/')} className={styles.backButton}>
            <ArrowLeft size={20} />
          </button>
        </div>

        <div className={styles.progress}>
          <div className={styles.progressText}>
            Питання {step + 1} з {fields.length}
          </div>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {currentField && (
          <div>
            <p className={styles.question}>{currentField.label}</p>

            {currentField.type === 'textarea' ? (
              <textarea
                className={styles.input}
                placeholder="Введіть відповідь..."
                value={answers[currentField.id] || ''}
                onChange={(e) => handleInputChange(e.target.value)}
                rows={4}
              />
            ) : currentField.type === 'select' && currentField.options ? (
              <select
                className={styles.input}
                value={answers[currentField.id] || ''}
                onChange={(e) => handleInputChange(e.target.value)}
              >
                <option value="">Оберіть...</option>
                {currentField.options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                ref={inputRef}
                type={currentField.type === 'number' ? 'number' : currentField.type || 'text'}
                className={styles.input}
                placeholder="Ваша відповідь..."
                value={answers[currentField.id] != null ? answers[currentField.id] : ''}
                onChange={(e) => handleInputChange(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleNext()}
              />
            )}

            {errors[currentField.id] && (
              <p className={styles.error}>{errors[currentField.id]}</p>
            )}

            <button
              onClick={handleNext}
              disabled={generating || !!errors[currentField.id]}
              className={styles.button}
            >
              {generating ? (
                <>
                  <Loader2 className="animate-spin inline mr-2" size={16} />
                  Генерація...
                </>
              ) : step === fields.length - 1 ? (
                <>
                  <Check size={16} className="inline mr-2" />
                  Згенерувати договір
                </>
              ) : (
                'Далі'
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}