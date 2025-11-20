import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.DEV ? 'http://localhost:8000' : '',
});

export const getContractTypes = () => api.get('/contracts/types').then((r: { data: any; }) => r.data);

export const generate = (type: string, answers: Record<string, any>) =>
  api.post('/contracts/generate', {
    contract_type: type,
    form_data: answers
  }).then((r: { data: any; }) => r.data);