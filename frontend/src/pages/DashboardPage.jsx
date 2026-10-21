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
import BudgetHistory from '../components/BudgetHistory';
import SpendingTrends from '../components/SpendingTrends';
import DataMiningPage from '../components/DataMiningPage'; 
import { useAuth } from '../context/AuthContext'; 

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export default function DashboardPage() {
  const { logout, token } = useAuth(); 

  const [file, setFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [hasData, setHasData] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  const [metrics, setMetrics] = useState({
    total_spend: 0,
    total_transactions: 0,
    forecast_7_days: [0, 0, 0, 0, 0, 0, 0],
    forecast_dates: [],
    recommended_savings: 0,
    categories: {},
    anomalies: [],
    transactions: [],
    recommendations: [],
    active_budgets: {}
  });

  const [timeRange, setTimeRange] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const fetchDashboardData = async () => {
    try {
      let url = `${API_BASE}/api/dashboard/?range=${timeRange}&category=${encodeURIComponent(selectedCategory)}`;
      if (timeRange === 'custom' && startDate && endDate) {
        url += `&start_date=${startDate}&end_date=${endDate}`;
      }

      const res = await fetch(url, {
        headers: { 'Authorization': `Token ${token}` }
      });
      
      if (res.status === 401) {
        logout(); 
        return;
      }

      const data = await res.json();

      setMetrics({
        total_spend: data.total_spend || 0,
        total_transactions: data.total_transactions || 0,
        forecast_7_days: data.forecast_7_days || [0, 0, 0, 0, 0, 0, 0],
        forecast_dates: data.forecast_dates || [],
        categories: data.categories || {},
        anomalies: data.anomalies || [],
        recommended_savings: data.recommended_savings || 0,
        transactions: data.transactions || [],
        recommendations: data.recommendations || [],
        active_budgets: data.active_budgets || {}
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
      const res = await fetch(`${API_BASE}/api/upload/`, {
        method: 'POST',
        headers: { 'Authorization': `Token ${token}` },
        body: formData,
      });

      if (!res.ok) throw new Error(`Server status ${res.status}`);

      await fetchDashboardData();
      setHasData(true);
      setActiveTab('overview'); 
    } catch (err) {
      console.error("Upload error:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const totalForecastSpend = metrics.forecast_7_days.reduce((acc, curr) => acc + curr, 0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased flex">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} logout={logout} />

      <main className="flex-1 p-6 md:p-10 max-w-7xl mx-auto space-y-8 overflow-y-auto">
        <Header
          file={file}
          isAnalyzing={isAnalyzing}
          handleFileChange={handleFileChange}
          handleUpload={handleUpload}
        />

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <>
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

            <MetricCards metrics={metrics} totalForecastSpend={totalForecastSpend} />

            {hasData && (
              <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <CategoryChart categories={metrics.categories} />
                <ForecastChart
                  forecastDataArray={metrics.forecast_7_days}
                  forecastDates={metrics.forecast_dates}
                />
              </section>
            )}

            <section className="w-full">
              <TransactionHistory
                transactions={metrics.transactions}
                onCategoryChanged={fetchDashboardData}
              />        
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <AnomalyTable anomalies={metrics.anomalies} />
              <BudgetOptimizer
                recommendations={metrics.recommendations}
                activeBudgets={metrics.active_budgets}
                onSuccess={fetchDashboardData}
              />
            </section>
          </>
        )}

        {/* Tab 2: Spending Trends */}
        {activeTab === 'trends' && <SpendingTrends />}

        {/* Tab 3: AI Data Models (PCA & Apriori) */}
        {activeTab === 'models' && <DataMiningPage />}

        {/* Tab 4: Budget History */}
        {activeTab === 'history' && <BudgetHistory />}
      </main>
    </div>
  );
}