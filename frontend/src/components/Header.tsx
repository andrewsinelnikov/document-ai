import { Shield } from 'lucide-react';
import styles from './Header.module.css';

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <Shield className={styles.icon} />
        <h1 className={styles.title}>Договір.ЗаХвилин</h1>
      </div>
      <p className={styles.subtitle}>Створіть юридичний договір за 5 хвилин без юриста</p>
    </header>
  );
}