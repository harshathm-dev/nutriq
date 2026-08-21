import React from 'react';
import { Sparkles } from 'lucide-react';
import { FoodRecommendationCard } from './FoodRecommendationCard';

export const SmartFoodRecommendations = ({
  recommendations = [],
  goalDisplay = '',
  onNavigateCatalog,
  onLogFood
}) => {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(16, 185, 129, 0.35)'
            }}
          >
            <Sparkles size={18} color="#fff" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', margin: 0, fontWeight: '800' }}>Smart Food Recommendations</h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              {goalDisplay ? `Personalized choices fitting your ${goalDisplay} goal & remaining nutrient budget` : 'Personalized food options grounded in the NutriQ catalog'}
            </span>
          </div>
        </div>

        {onNavigateCatalog && (
          <button
            onClick={onNavigateCatalog}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.78rem' }}
          >
            Browse Catalog
          </button>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
        {recommendations.map((rec, idx) => (
          <FoodRecommendationCard
            key={idx}
            recommendation={rec}
            onLogFood={onLogFood}
          />
        ))}
      </div>
    </div>
  );
};

export default SmartFoodRecommendations;
