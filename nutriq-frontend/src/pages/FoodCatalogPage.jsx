import React from 'react';
import { useStore } from '../store/useStore';
import { FoodTabs } from '../components/FoodTabs';
import { BookOpen, Plus, Sparkles } from 'lucide-react';

export const FoodCatalogPage = () => {
  const { navigate } = useStore();

  const handleSelectFood = (food) => {
    navigate(`/log-meal?prefill_food=${encodeURIComponent(food.name)}`);
  };

  return (
    <div className="page-container">
      {/* Header Panel */}
      <div className="wellness-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '44px',
              height: '44px',
              borderRadius: '12px',
              background: 'var(--primary-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(31, 122, 90, 0.25)'
            }}>
              <BookOpen size={24} color="#FFFFFF" />
            </div>
            <div>
              <h1 style={{ fontSize: '1.6rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                Food Catalog & Favorites
              </h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', margin: '4px 0 0 0' }}>
                Master dataset of verified Indian & global foods with complete macro profiles and offline support.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => navigate('/log-meal')}
            className="btn-primary"
            style={{ padding: '9px 18px', fontSize: '0.86rem' }}
          >
            <Plus size={16} /> Log a Meal
          </button>
        </div>
      </div>

      {/* 3-Tab Experience (Catalog, Recent, Favorites) */}
      <FoodTabs
        onSelectFood={handleSelectFood}
        onAddFood={handleSelectFood}
        defaultTab="catalog"
        allowSearch={true}
      />
    </div>
  );
};
