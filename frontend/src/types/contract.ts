export type ContractType = 
  | "Оренда квартири"
  | "Надання послуг (ФОП)"
  | "NDA"
  | "Позика";

// export type ContractType = 'rent_contract' | 'loan_contract' | 'nda_contract' | 'service_contract';

export interface UserAnswer {
  question: string;
  answer: string;
}

export interface ContractResult {
  contract_type: ContractType;
  title: string;
  content_markdown: string;
  content_html: string;          
  content_pdf_base64: string;    
  generated_at: string;
}
