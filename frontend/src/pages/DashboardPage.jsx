import React, { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import FilterBar from '../components/FilterBar';
import MetricCards from '../components/MetricCards';
import CategoryChart from '../components/CategoryChart';
import ForecastChart from '../components/ForecastChart';
import AnomalyTable from '../components/AnomalyTable';
import BudgetOptimizer from '../components/BudgetOptimizer';
import TransactionHistory from '../components/TransactionHistory';

export default function DashboardPage() {
  const [file, setFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [hasData, setHasData] = useState(true);

  const [metrics, setMetrics] = useState({
    total_spend: 0,
    total_transactions: 0,
    forecast_7_days: [0, 0, 0, 0, 0, 0, 0],
    recommended_savings: 0,
    categories: {},
    anomalies: [],
    transactions: [],
    recommendations: [],
    active_budgets: {} // <--- Added active budgets state initialization
  });

  const [timeRange, setTimeRange] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const fetchDashboardData = async () => {
    try {
      let url = `http://127.0.0.1:8000/api/dashboard/?range=${timeRange}&category=${encodeURIComponent(selectedCategory)}`;
      if (timeRange === 'custom' && startDate && endDate) {
        url += `&start_date=${startDate}&end_date=${endDate}`;
      }

      const res = await fetch(url);
      const data = await res.json();

      setMetrics({
        total_spend: data.total_spend || 0,
        total_transactions: data.total_transactions || 0,
        forecast_7_days: data.forecast_7_days || [0, 0, 0, 0, 0, 0, 0],
        categories: data.categories || {},
        anomalies: data.anomalies || [],
        recommended_savings: data.recommended_savings || 0,
        transactions: data.transactions || [],
        recommendations: data.recommendations || [],
        active_budgets: data.active_budgets || {} // <--- Pull active budgets from API response
      });
    } catch (err) {
      console.error("Fetch error:", err);
    }
  };

  useEffect(() => {
    if (timeRange !== 'custom' || (startDate && endDate)) {
      fetchDashboardData();
    }
  }, [timeRange, selectedCategory, startDate, endDate]);

  const handleFileChange = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsAnalyzing(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/upload/', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`Server status ${res.status}`);

      await fetchDashboardData();
      setHasData(true);
    } catch (err) {
      console.error("Upload error:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const totalForecastSpend = metrics.forecast_7_days.reduce((acc, curr) => acc + curr, 0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased flex">
      <Sidebar />

      <main className="flex-1 p-6 md:p-10 max-w-7xl mx-auto space-y-8 overflow-y-auto">
        <Header 
          file={file} 
          isAnalyzing={isAnalyzing} 
          handleFileChange={handleFileChange} 
          handleUpload={handleUpload} 
        />

        <FilterBar 
          timeRange={timeRange} 
          setTimeRange={setTimeRange} 
          selectedCategory={selectedCategory} 
          setSelectedCategory={setSelectedCategory} 
          categories={metrics.categories}
          startDate={startDate}
          setStartDate={setStartDate}
          endDate={endDate}
          setEndDate={setEndDate}
        />

        <MetricCards 
          metrics={metrics} 
          totalForecastSpend={totalForecastSpend} 
        />

        {hasData && (
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <CategoryChart categories={metrics.categories} />
            <ForecastChart forecastDataArray={metrics.forecast_7_days} />
          </section>
        )}

        <section className="w-full">
          <TransactionHistory transactions={metrics.transactions} />
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <AnomalyTable anomalies={metrics.anomalies} />
          <BudgetOptimizer 
            recommendations={metrics.recommendations} 
            activeBudgets={metrics.active_budgets} 
          />
        </section>
      </main>
    </div>
  );
}