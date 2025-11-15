export type ContractType = 
  | "Оренда квартири"
  | "Надання послуг (ФОП)"
  | "NDA"
  | "Позика";

export interface UserAnswer {
  question: string;
  answer: string;
}
