import { useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { api, type ContractField } from '../api/api';
import styles from './ContractFlow.module.css';
import { Loader2, ArrowLeft, Check } from 'lucide-react';

export default function ContractFlow() {
  const { state } = useLocation();
  const { type } = (state || {}) as { type: string };
  const navigate = useNavigate();

  const [template, setTemplate] = useState<any>(null);
  const [fields, setFields] = useState<ContractField[]>([]);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatedContract, setGeneratedContract] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!type) {
      navigate('/');
      return;
    }

    api.getTemplate(type)
      .then((tmpl) => {
        setTemplate(tmpl);
        // Фільтруємо видимі поля (без умовних, які залежать від інших)
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

  const handleNext = async () => {
    if (!currentField) return;

    const value = answers[currentField.id] || '';
    setErrors({});

    // Клієнтська валідація
    if (currentField.required && !value.trim()) {
      setErrors({ [currentField.id]: 'Це поле обов’язкове' });
      return;
    }

    if (step === fields.length - 1) {
      // Генерація
      setGenerating(true);
      try {
        const result = await api.generate(type, answers);
        setGeneratedContract(result.content);
      } catch (err: any) {
        alert(err.message || 'Помилка генерації договору');
      } finally {
        setGenerating(false);
      }
    } else {
      setStep(step + 1);
    }
  };

  const handleInputChange = (value: string) => {
    setAnswers({ ...answers, [currentField.id]: value });
    if (errors[currentField.id]) {
      setErrors({ ...errors, [currentField.id]: '' });
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
          <button
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
                type={currentField.type === 'number' ? 'number' : 'text'}
                className={styles.input}
                placeholder="Ваша відповідь..."
                value={answers[currentField.id] || ''}
                onChange={(e) => handleInputChange(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleNext()}
              />
            )}

            {errors[currentField.id] && (
              <p className={styles.error}>{errors[currentField.id]}</p>
            )}

            <button
              onClick={handleNext}
              disabled={generating}
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