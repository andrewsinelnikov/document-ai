export type ContractType = 'rent_contract' | 'loan_contract' | 'nda_contract' | 'service_contract';

// export type ContractType = 
//   | "Оренда квартири"
//   | "Надання послуг (ФОП)"
//   | "NDA"
//   | "Позика";

export interface UserAnswer {
  question: string;
  answer: string;
}

export interface FormField {
  id: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'textarea';
  required?: boolean;
}

export interface ContractResult {
  contract_type: ContractType;
  title: string;
  content_markdown: string;
  content_html: string;          
  content_pdf_base64: string;    
  generated_at: string;
}
