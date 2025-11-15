import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Home from './pages/Home';
import ContractFlow from './pages/ContractFlow';
import styles from './App.module.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className={styles.app}>
        <Header />
        <main className={styles.main}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/contract" element={<ContractFlow />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}