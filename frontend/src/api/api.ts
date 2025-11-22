import axios from 'axios';
import type { ContractResult } from '../types/contract';

const api = axios.create({
  baseURL: import.meta.env.DEV ? 'http://localhost:8000' : '',
  timeout: 90_000, // генерація може займати до 60–80 сек
});

// ───── Типи ─────
export interface ContractTypeResponse {
  id: string;
  title: string;
}

export interface GenerateResponse {
  contract_type: string;
  title: string;
  content_markdown: string;
  content_pdf_base64?: string;
  generated_at: string;
}

// ───── Функції ─────
export const getContractTypes = () =>
  api.get<ContractTypeResponse[]>('/contracts/types').then(r => r.data);

// export const generate = (type: string, answers: Record<string, any>) =>
//   api.post('/contracts/generate', {
//     contract_type: type,
//     form_data: answers,
//   }).then(r => r.data);   

export const generate = async (contractType: string, formData: Record<string, any>) => {
  const res = await fetch('/contracts/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contract_type: contractType,
      form_data: formData,
    }),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || 'Помилка сервера');
  }

  return (await res.json()) as ContractResult;
};  
// (необов’язково) можна ще додати тип для generate
export const generateTyped = (type: string, answers: Record<string, any>): Promise<GenerateResponse> =>
  generate(type, answers);