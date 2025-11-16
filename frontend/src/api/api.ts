const API_BASE = 'http://127.0.0.1:8000';

export interface ContractTypeResponse {
  id: string;
  title: string;
  description: string;
}

export interface ContractField {
  id: string;
  label: string;
  type: string;
  required: boolean;
  options?: Array<{ value: string; label: string }>;
  validation?: Record<string, any>;
  conditional?: Record<string, any>;
}

export interface ContractTemplate {
  id: string;
  title: string;
  description: string;
  fields: ContractField[];
  template: any;
}

export const api = {
  // Отримати типи договорів
  getContractTypes: async (): Promise<ContractTypeResponse[]> => {
    const res = await fetch(`${API_BASE}/contracts/types`);
    if (!res.ok) throw new Error('Не вдалося завантажити типи договорів');
    return res.json();
  },

  // Отримати шаблон
  getTemplate: async (type: string): Promise<ContractTemplate> => {
    const res = await fetch(`${API_BASE}/contracts/${type}/template`);
    if (!res.ok) throw new Error('Шаблон не знайдено');
    return res.json();
  },

  // Валідація
  validate: async (contract_type: string, form_data: Record<string, any>) => {
    const res = await fetch(`${API_BASE}/contracts/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contract_type, form_data }),
    });
    return res.json();
  },

  // Генерація
  generate: async (contract_type: string, form_data: Record<string, any>) => {
    const res = await fetch(`${API_BASE}/contracts/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contract_type, form_data }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail?.message || 'Помилка генерації');
    }
    return res.json();
  },
};