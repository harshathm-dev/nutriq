import React, { useState, useEffect } from 'react';
import { Clock, Heart, Sparkles, Search, BookOpen, AlertCircle, RefreshCw } from 'lucide-react';
import { FoodCard } from './FoodCard';
import { api } from '../services/api';

export const FoodTabs = ({
  onSelectFood,
  onAddFood,
  selectedFoodId = null,
  compact = false,
  defaultTab = 'catalog',
  allowSearch = true
}) => {
  const [activeTab, setActiveTab] = useState(defaultTab); // 'catalog' | 'recent' | 'favorites'
  const [recentFoods, setRecentFoods] = useState([]);
  const [favoriteFoods, setFavoriteFoods] = useState([]);
  const [catalogFoods, setCatalogFoods] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  const categories = [
    'All',
    'South Indian',
    'North Indian',
    'Rice',
    'Dosa',
    'Idli',
    'Curries',
    'Gravies',
    'Sambar',
    'Rasam',
    'Snacks',
    'Breakfast',
    'Lunch',
    'Dinner',
    'Sweets',
    'Beverages'
  ];

  useEffect(() => {
    loadTabData(activeTab);
  }, [activeTab]);

  const loadTabData = async (tab) => {
    setLoading(true);
    try {
      if (tab === 'recent') {
        const recent = await api.getRecentFoods(24);
        setRecentFoods(recent || []);
      } else if (tab === 'favorites') {
        const favs = await api.getFavoriteFoods();
        setFavoriteFoods(favs || []);
      } else if (tab === 'catalog') {
        const foods = await api.searchFoods(searchQuery, selectedCategory === 'All' ? '' : selectedCategory);
        setCatalogFoods(foods || []);
      }
    } catch (err) {
      console.warn(`Error loading tab data for ${tab}:`, err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    try {
      const foods = await api.searchFoods(searchQuery, selectedCategory === 'All' ? '' : selectedCategory);
      setCatalogFoods(foods || []);
    } catch (err) {
      console.warn("Search error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryClick = (cat) => {
    setSelectedCategory(cat);
    setLoading(true);
    api.searchFoods(searchQuery, cat === 'All' ? '' : cat)
      .then(res => setCatalogFoods(res || []))
      .catch(() => setCatalogFoods([]))
      .finally(() => setLoading(false));
  };

  const currentDisplayList = activeTab === 'recent'
    ? recentFoods
    : activeTab === 'favorites'
      ? favoriteFoods
      : catalogFoods;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* 3-Tab Selector Pill Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px',
        background: 'var(--bg-subtle)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-glass)',
        width: 'fit-content'
      }}>
        <button
          type="button"
          onClick={() => setActiveTab('catalog')}
          style={{
            padding: '8px 18px',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            background: activeTab === 'catalog' ? 'var(--bg-active-tab, #FFFFFF)' : 'transparent',
            color: activeTab === 'catalog' ? 'var(--primary)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'catalog' ? '800' : '600',
            fontSize: '0.84rem',
            cursor: 'pointer',
            boxShadow: activeTab === 'catalog' ? 'var(--shadow-sm)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.16s ease'
          }}
        >
          <BookOpen size={16} /> All Catalog
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('recent')}
          style={{
            padding: '8px 18px',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            background: activeTab === 'recent' ? 'var(--bg-active-tab, #FFFFFF)' : 'transparent',
            color: activeTab === 'recent' ? 'var(--primary)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'recent' ? '800' : '600',
            fontSize: '0.84rem',
            cursor: 'pointer',
            boxShadow: activeTab === 'recent' ? 'var(--shadow-sm)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.16s ease'
          }}
        >
          <Clock size={16} /> Recent Foods
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('favorites')}
          style={{
            padding: '8px 18px',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            background: activeTab === 'favorites' ? 'var(--bg-active-tab, #FFFFFF)' : 'transparent',
            color: activeTab === 'favorites' ? 'var(--calorie-orange, #FF6B4A)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'favorites' ? '800' : '600',
            fontSize: '0.84rem',
            cursor: 'pointer',
            boxShadow: activeTab === 'favorites' ? 'var(--shadow-sm)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.16s ease'
          }}
        >
          <Heart size={16} fill={activeTab === 'favorites' ? "var(--calorie-orange, #FF6B4A)" : "none"} color="var(--calorie-orange, #FF6B4A)" /> Favorites
        </button>
      </div>

      {/* Catalog Search & Category Filters (Active on catalog tab) */}
      {activeTab === 'catalog' && allowSearch && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '10px' }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                className="input-field"
                placeholder="Search food items (e.g. Masala Dosa, Paneer, Rice, Dal)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ paddingLeft: '38px', height: '42px', fontSize: '0.9rem' }}
              />
            </div>
            <button type="submit" className="btn-primary" style={{ padding: '0 20px', height: '42px' }}>
              Search
            </button>
          </form>

          {/* Category Filter Chips */}
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
            {categories.map((cat) => {
              const isSelected = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => handleCategoryClick(cat)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 'var(--radius-full)',
                    border: isSelected ? '1px solid #2563EB' : '1px solid #BFDBFE',
                    background: isSelected ? '#2563EB' : '#EFF6FF',
                    color: isSelected ? '#FFFFFF' : '#1D4ED8',
                    fontWeight: isSelected ? '700' : '600',
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    boxShadow: isSelected ? '0 2px 8px rgba(37, 99, 235, 0.35)' : 'none',
                    transition: 'all 0.16s ease'
                  }}
                  onMouseEnter={(e) => {
                    if (isSelected) {
                      e.currentTarget.style.background = '#1D4ED8';
                      e.currentTarget.style.borderColor = '#1D4ED8';
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(37, 99, 235, 0.45)';
                    } else {
                      e.currentTarget.style.background = '#DBEAFE';
                      e.currentTarget.style.color = '#1D4ED8';
                      e.currentTarget.style.borderColor = '#60A5FA';
                      e.currentTarget.style.boxShadow = '0 2px 6px rgba(37, 99, 235, 0.15)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (isSelected) {
                      e.currentTarget.style.background = '#2563EB';
                      e.currentTarget.style.color = '#FFFFFF';
                      e.currentTarget.style.borderColor = '#2563EB';
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(37, 99, 235, 0.35)';
                    } else {
                      e.currentTarget.style.background = '#EFF6FF';
                      e.currentTarget.style.color = '#1D4ED8';
                      e.currentTarget.style.borderColor = '#BFDBFE';
                      e.currentTarget.style.boxShadow = 'none';
                    }
                  }}
                >
                  {cat}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Food Cards Grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)' }}>
          Loading nutrition catalog...
        </div>
      ) : currentDisplayList.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '36px 20px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-lg)' }}>
          <AlertCircle size={32} color="var(--text-muted)" style={{ margin: '0 auto 8px auto' }} />
          <h4 style={{ fontSize: '1.02rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
            {activeTab === 'favorites' ? "No favorite foods saved yet" : activeTab === 'recent' ? "No recently logged foods found" : "No foods match your search"}
          </h4>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
            {activeTab === 'favorites' ? "Click the heart icon on any food to save it here for fast access." : "Try clearing filters or searching for another ingredient."}
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '14px' }}>
          {currentDisplayList.map((food) => (
            <FoodCard
              key={food.id || food.food_id}
              food={food}
              onAddFood={onAddFood}
              onSelectFood={onSelectFood}
              isSelected={selectedFoodId === (food.id || food.food_id)}
              compact={compact}
            />
          ))}
        </div>
      )}

    </div>
  );
};
