import styles from './Footer.module.css';

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.content}>
        <p>Працює на AI • Не заміна юриста • Інтеграція з Дія.Підпис</p>
      </div>
    </footer>
  );
}
