import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore.js';
import { api } from '../services/api.js';
import { getToday, formatDate } from '../utils/dateUtils.js';
import {
  Search, Plus, Minus, Check, Trash2, AlertCircle, RefreshCw,
  Utensils, ChevronRight, CheckCircle2, Flame, Sparkles, X, RotateCcw,
  Clock, Heart, ArrowRight
} from 'lucide-react';

export const AddFoodPage = () => {
  const [mealType, setMealType] = useState('breakfast');
  const [sourceTab, setSourceTab] = useState('all'); // 'all' | 'recent' | 'favorites'
  
  // Search & Catalog state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState('');

  // Explicit Food Selection & Configuration state
  const [configuringFood, setConfiguringFood] = useState(null);
  const [inputQuantity, setInputQuantity] = useState(1);
  const [inputUnit, setInputUnit] = useState('100g');
  const [unitGrams, setUnitGrams] = useState(100.0);

  // Staged Meal Items (Basket)
  const [selectedItems, setSelectedItems] = useState([]);

  // Save meal state
  const [isSaving, setIsSaving] = useState(false);
  const { refreshAllData, navigate } = useStore();
  const [targetDate, setTargetDate] = useState(() => getToday());
  const [mealTime, setMealTime] = useState(() => {
    const now = new Date();
    return String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
  });

  useEffect(() => {
    let prefill = '';
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const paramDate = params.get('date');
      if (paramDate && /^\d{4}-\d{2}-\d{2}$/.test(paramDate)) {
        setTargetDate(paramDate);
      }
      const paramMealType = params.get('meal_type');
      if (paramMealType && ['breakfast', 'lunch', 'snack', 'dinner', 'other'].includes(paramMealType.toLowerCase())) {
        setMealType(paramMealType.toLowerCase());
      }
      prefill = params.get('prefill_food') || '';
      if (prefill) {
        setSearchQuery(prefill);
      }
    }
    fetchTabData('all', prefill);
  }, []);

  const fetchTabData = async (tab, q = '') => {
    setIsSearching(true);
    setSearchError('');
    try {
      let results = [];
      if (tab === 'recent') {
        results = await api.getRecentFoods(30);
        if (q) {
          results = results.filter(f => f.name.toLowerCase().includes(q.toLowerCase()));
        }
      } else if (tab === 'favorites') {
        results = await api.getFavoriteFoods();
        if (q) {
          results = results.filter(f => f.name.toLowerCase().includes(q.toLowerCase()));
        }
      } else {
        results = await api.searchFoods(q);
      }
      setSearchResults(results || []);
    } catch (e) {
      console.warn("Error loading tab foods:", e);
      setSearchError("Unable to load food results. Please try again.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleSourceTabClick = (tab) => {
    setSourceTab(tab);
    fetchTabData(tab, searchQuery);
  };

  const handleSearch = (q) => {
    fetchTabData(sourceTab, q);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    fetchTabData(sourceTab, '');
  };

  const handleToggleFavorite = async (e, food) => {
    e.stopPropagation();
    try {
      const nextFav = !food.is_favorite;
      await api.toggleFavoriteFood(food.id, !nextFav);
      setSearchResults(prev => prev.map(f => f.id === food.id ? { ...f, is_favorite: nextFav } : f));
      if (sourceTab === 'favorites' && !nextFav) {
        setSearchResults(prev => prev.filter(f => f.id !== food.id));
      }
    } catch (err) {
      console.warn("Failed to toggle favorite:", err);
    }
  };

  const handleOpenConfigurator = (food, defaultConv = null) => {
    setConfiguringFood(food);
    setInputQuantity(1);
    if (defaultConv) {
      setInputUnit(defaultConv.serving_label);
      setUnitGrams(defaultConv.grams);
    } else if (food.serving_conversions && food.serving_conversions.length > 0) {
      setInputUnit(food.serving_conversions[0].serving_label);
      setUnitGrams(food.serving_conversions[0].grams);
    } else {
      setInputUnit(`${food.serving_size || 100} ${food.unit || 'g'}`);
      setUnitGrams(food.serving_size || 100.0);
    }
  };

  const handleUnitChange = (servingLabel) => {
    setInputUnit(servingLabel);
    if (!configuringFood) return;
    const conv = configuringFood.serving_conversions?.find(c => c.serving_label === servingLabel);
    if (conv) {
      setUnitGrams(conv.grams);
    } else {
      setUnitGrams(configuringFood.serving_size || 100.0);
    }
  };

  const handleConfirmAddConfigured = () => {
    if (!configuringFood) return;
    const qty = Math.max(0.01, parseFloat(inputQuantity) || 1.0);
    const totalGrams = unitGrams * qty;
    const mult = totalGrams / 100.0;

    const newItem = {
      food_id: configuringFood.id,
      food_name: configuringFood.name,
      name: configuringFood.name,
      quantity: qty,
      portion: qty,
      serving_unit: inputUnit,
      unit_grams: unitGrams,
      grams: Math.round(totalGrams * 10) / 10,
      calories: Math.round((configuringFood.calories || 0) * mult),
      protein_g: Math.round((configuringFood.protein_g || configuringFood.protein || 0) * mult * 10) / 10,
      protein: Math.round((configuringFood.protein_g || configuringFood.protein || 0) * mult * 10) / 10,
      carbs_g: Math.round((configuringFood.carbs_g || configuringFood.carbs || 0) * mult * 10) / 10,
      carbs: Math.round((configuringFood.carbs_g || configuringFood.carbs || 0) * mult * 10) / 10,
      fat_g: Math.round((configuringFood.fat_g || configuringFood.fat || 0) * mult * 10) / 10,
      fat: Math.round((configuringFood.fat_g || configuringFood.fat || 0) * mult * 10) / 10,
      fiber_g: Math.round((configuringFood.fiber_g || configuringFood.fiber || 0) * mult * 10) / 10,
      fiber: Math.round((configuringFood.fiber_g || configuringFood.fiber || 0) * mult * 10) / 10
    };

    setSelectedItems([...selectedItems, newItem]);
    setConfiguringFood(null);
  };

  const handleUpdateItemQuantity = (index, deltaOrValue) => {
    const updated = [...selectedItems];
    const item = { ...updated[index] };
    let newQty = item.quantity || item.portion || 1;

    if (typeof deltaOrValue === 'number') {
      newQty = Math.max(0.25, Math.round((newQty + deltaOrValue) * 100) / 100);
    } else {
      const parsed = parseFloat(deltaOrValue);
      if (!isNaN(parsed) && parsed > 0) {
        newQty = parsed;
      }
    }

    const currentQty = item.quantity || item.portion || 1.0;
    const ratio = newQty / currentQty;

    item.quantity = newQty;
    item.portion = newQty;
    item.grams = Math.round((item.grams || 100) * ratio * 10) / 10;
    item.calories = Math.round(item.calories * ratio);
    item.protein_g = Math.round(item.protein_g * ratio * 10) / 10;
    item.carbs_g = Math.round(item.carbs_g * ratio * 10) / 10;
    item.fat_g = Math.round(item.fat_g * ratio * 10) / 10;
    if (item.fiber_g) item.fiber_g = Math.round(item.fiber_g * ratio * 10) / 10;

    updated[index] = item;
    setSelectedItems(updated);
  };

  const handleRemoveItem = (index) => {
    setSelectedItems(selectedItems.filter((_, i) => i !== index));
  };

  const handleSaveMeal = async () => {
    if (selectedItems.length === 0 || isSaving) return;
    setIsSaving(true);
    try {
      await api.createMeal({
        meal_type: mealType,
        date: targetDate,
        time: mealTime,
        source: 'search',
        items: selectedItems
      });
      await refreshAllData();
      navigate(`/meal-history?date=${targetDate}`);
    } catch (err) {
      alert("Failed to save meal: " + (err.message || "Unknown error"));
    } finally {
      setIsSaving(false);
    }
  };

  const totalKcal = selectedItems.reduce((acc, i) => acc + (i.calories || 0), 0);
  const totalProtein = selectedItems.reduce((acc, i) => acc + (i.protein_g || i.protein || 0), 0);
  const totalCarbs = selectedItems.reduce((acc, i) => acc + (i.carbs_g || i.carbs || 0), 0);
  const totalFat = selectedItems.reduce((acc, i) => acc + (i.fat_g || i.fat || 0), 0);
  const totalFiber = selectedItems.reduce((acc, i) => acc + (i.fiber_g || i.fiber || 0), 0);

  // Live preview for configuring food
  const previewQty = Math.max(0.01, parseFloat(inputQuantity) || 1.0);
  const previewGrams = unitGrams * previewQty;
  const previewMult = previewGrams / 100.0;
  const previewKcal = configuringFood ? Math.round((configuringFood.calories || 0) * previewMult) : 0;
  const previewPro = configuringFood ? Math.round((configuringFood.protein_g || configuringFood.protein || 0) * previewMult * 10) / 10 : 0;
  const previewCarb = configuringFood ? Math.round((configuringFood.carbs_g || configuringFood.carbs || 0) * previewMult * 10) / 10 : 0;
  const previewFat = configuringFood ? Math.round((configuringFood.fat_g || configuringFood.fat || 0) * previewMult * 10) / 10 : 0;
  const previewFiber = configuringFood ? Math.round((configuringFood.fiber_g || configuringFood.fiber || 0) * previewMult * 10) / 10 : 0;

  return (
    <div className="page-container">
      
      {/* 1. Header & Meal Type / Date Selector */}
      <div className="wellness-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', marginBottom: '4px' }}>
              <Utensils size={20} />
              <h2 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>Log Meal</h2>
            </div>
            <span style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
              Select foods, configure portions, and record your meal nutrition for {formatDate(targetDate)}.
            </span>
          </div>

          {/* Date & Time Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: '700', color: 'var(--text-muted)', marginBottom: '2px' }}>
                Meal Date
              </label>
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="input-field"
                style={{ height: '36px', fontSize: '0.82rem', padding: '4px 10px' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: '700', color: 'var(--text-muted)', marginBottom: '2px' }}>
                Time
              </label>
              <input
                type="time"
                value={mealTime}
                onChange={(e) => setMealTime(e.target.value)}
                className="input-field"
                style={{ height: '36px', fontSize: '0.82rem', padding: '4px 10px' }}
              />
            </div>
          </div>
        </div>

        {/* Meal Type Selector Buttons */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '16px' }}>
          {[
            { key: 'breakfast', label: '🌅 Breakfast' },
            { key: 'lunch', label: '☀️ Lunch' },
            { key: 'snack', label: '☕ Snack' },
            { key: 'dinner', label: '🌙 Dinner' }
          ].map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setMealType(key)}
              className={mealType === key ? "btn-primary" : "btn-secondary"}
              style={{ padding: '8px 16px', fontSize: '0.84rem' }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* 2. Main Two-Column Layout: Food Selector (Left ~60-65%) & Meal Basket (Right ~35-40%) */}
      <div className="log-meal-grid">
        
        {/* Left Column: Search & Food Catalog */}
        <div className="wellness-card" style={{ padding: '24px', width: '100%', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', gap: '12px', flexWrap: 'wrap' }}>
            {/* 3 Source Tabs */}
            <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-subtle)', padding: '4px', borderRadius: 'var(--radius-md)' }}>
              <button
                type="button"
                onClick={() => handleSourceTabClick('all')}
                style={{
                  padding: '6px 16px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  background: sourceTab === 'all' ? 'var(--bg-active-tab, #FFFFFF)' : 'transparent',
                  color: sourceTab === 'all' ? 'var(--primary)' : 'var(--text-secondary)',
                  fontWeight: sourceTab === 'all' ? '800' : '600',
                  fontSize: '0.8rem',
                  cursor: 'pointer'
                }}
              >
                All Foods
              </button>
              <button
                type="button"
                onClick={() => handleSourceTabClick('recent')}
                style={{
                  padding: '6px 16px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  background: sourceTab === 'recent' ? 'var(--bg-active-tab, #FFFFFF)' : 'transparent',
                  color: sourceTab === 'recent' ? 'var(--primary)' : 'var(--text-secondary)',
                  fontWeight: sourceTab === 'recent' ? '800' : '600',
                  fontSize: '0.8rem',
                  cursor: 'pointer'
                }}
              >
                Recent
              </button>
              <button
                type="button"
                onClick={() => handleSourceTabClick('favorites')}
                style={{
                  padding: '6px 16px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  background: sourceTab === 'favorites' ? 'var(--bg-active-tab, #FFFFFF)' : 'transparent',
                  color: sourceTab === 'favorites' ? 'var(--calorie-orange, #E76F51)' : 'var(--text-secondary)',
                  fontWeight: sourceTab === 'favorites' ? '800' : '600',
                  fontSize: '0.8rem',
                  cursor: 'pointer'
                }}
              >
                Favorites
              </button>
            </div>
          </div>

          {/* Search Input */}
          <div style={{ position: 'relative', marginBottom: '16px' }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              className="input-field"
              placeholder="Search food items (e.g. Dosa, Rice, Paneer, Chicken, Oats)..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                handleSearch(e.target.value);
              }}
              style={{ paddingLeft: '38px', height: '42px', fontSize: '0.9rem' }}
            />
          </div>

          {/* Food List */}
          {isSearching ? (
            <div style={{ textAlign: 'center', padding: '36px', color: 'var(--text-secondary)' }}>
              Loading foods...
            </div>
          ) : searchResults.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '36px', color: 'var(--text-secondary)' }}>
              No foods found. Try another search term.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: 'calc(100vh - 360px)', minHeight: '340px', overflowY: 'auto', paddingRight: '4px' }}>
              {searchResults.map((food) => (
                <div
                  key={food.id}
                  onClick={() => handleOpenConfigurator(food)}
                  style={{
                    padding: '14px 18px',
                    borderRadius: 'var(--radius-md)',
                    background: configuringFood?.id === food.id ? 'var(--primary-light)' : 'var(--bg-subtle)',
                    border: configuringFood?.id === food.id ? '1.5px solid var(--primary)' : '1px solid var(--border-glass)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.16s ease'
                  }}
                  onMouseEnter={(e) => {
                    if (configuringFood?.id !== food.id) {
                      e.currentTarget.style.borderColor = 'var(--primary)';
                      e.currentTarget.style.background = 'var(--bg-elevated, #FFFFFF)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (configuringFood?.id !== food.id) {
                      e.currentTarget.style.borderColor = 'var(--border-glass)';
                      e.currentTarget.style.background = 'var(--bg-subtle)';
                    }
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '0.94rem', fontWeight: '800', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {food.name}
                    </div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {Math.round(food.calories || 0)} kcal • P: {Math.round(food.protein_g || food.protein || 0)}g • C: {Math.round(food.carbs_g || food.carbs || 0)}g • F: {Math.round(food.fat_g || food.fat || 0)}g
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                    <button
                      type="button"
                      onClick={(e) => handleToggleFavorite(e, food)}
                      style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px', color: food.is_favorite ? '#E76F51' : 'var(--text-muted)' }}
                    >
                      <Heart size={18} fill={food.is_favorite ? "#E76F51" : "none"} />
                    </button>
                    <span className="btn-primary" style={{ padding: '6px 12px', fontSize: '0.78rem', borderRadius: 'var(--radius-sm)' }}>
                      Add Portion
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Portion Configurator & Staged Meal Basket */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', alignSelf: 'start', height: 'fit-content' }}>
          
          {/* Portion Configurator Card */}
          {configuringFood && (
            <div className="wellness-card" style={{ padding: '20px', border: '1.5px solid var(--primary)', background: 'var(--bg-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <h4 style={{ fontSize: '1.05rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                  Configure Portion
                </h4>
                <button
                  type="button"
                  onClick={() => setConfiguringFood(null)}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                >
                  <X size={18} />
                </button>
              </div>

              <div style={{ fontSize: '0.92rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '14px' }}>
                {configuringFood.name}
              </div>

              {/* Quantity & Serving Unit Inputs */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: '10px', marginBottom: '14px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Quantity
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="20"
                    value={inputQuantity}
                    onChange={(e) => setInputQuantity(e.target.value)}
                    className="input-field"
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Serving Unit
                  </label>
                  {configuringFood.serving_conversions && configuringFood.serving_conversions.length > 0 ? (
                    <select
                      value={inputUnit}
                      onChange={(e) => handleUnitChange(e.target.value)}
                      className="input-field"
                    >
                      {configuringFood.serving_conversions.map((conv, idx) => (
                        <option key={idx} value={conv.serving_label}>
                          {conv.serving_label} ({conv.grams}g)
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      disabled
                      value={inputUnit}
                      className="input-field"
                    />
                  )}
                </div>
              </div>

              {/* Portion Live Preview */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-elevated, #FFFFFF)', padding: '10px 14px', borderRadius: 'var(--radius-md)', marginBottom: '14px' }}>
                <div>
                  <span style={{ fontSize: '0.98rem', fontWeight: '800', color: 'var(--calorie-orange)' }}>
                    {previewKcal} kcal
                  </span>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    P: {previewPro}g • C: {previewCarb}g • F: {previewFat}g • Fib: {previewFiber}g
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleConfirmAddConfigured}
                  className="btn-primary"
                  style={{ padding: '7px 16px', fontSize: '0.82rem' }}
                >
                  <Plus size={15} /> Add to Meal
                </button>
              </div>
            </div>
          )}

          {/* Staged Meal Items (Basket) */}
          <div className="wellness-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                  Current Meal Basket ({selectedItems.length})
                </h3>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                  Logging to {mealType}
                </span>
              </div>

              {selectedItems.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSelectedItems([])}
                  className="btn-secondary"
                  style={{ padding: '4px 10px', fontSize: '0.75rem', color: 'var(--error-rose)' }}
                >
                  Clear All
                </button>
              )}
            </div>

            {selectedItems.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '36px 16px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                <Utensils size={32} color="var(--text-muted)" style={{ margin: '0 auto 8px auto' }} />
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', margin: 0 }}>
                  Your meal basket is empty. Select foods from the catalog to build this meal.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
                {selectedItems.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 14px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-subtle)',
                      border: '1px solid var(--border-glass)'
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                        {item.food_name || item.name}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                        {item.portion || item.quantity}x {item.serving_unit || 'serving'} • {item.calories} kcal
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--bg-elevated, #FFFFFF)', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-glass)' }}>
                        <button
                          type="button"
                          onClick={() => handleUpdateItemQuantity(idx, -0.5)}
                          style={{ border: 'none', background: 'transparent', padding: '2px 6px', cursor: 'pointer', fontWeight: '800' }}
                        >
                          -
                        </button>
                        <span style={{ fontSize: '0.78rem', fontWeight: '800', minWidth: '24px', textAlign: 'center' }}>
                          {item.quantity || item.portion}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleUpdateItemQuantity(idx, 0.5)}
                          style={{ border: 'none', background: 'transparent', padding: '2px 6px', cursor: 'pointer', fontWeight: '800' }}
                        >
                          +
                        </button>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleRemoveItem(idx)}
                        style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--error-rose)', padding: '4px' }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Total Nutritional Summary & Log Action */}
            {selectedItems.length > 0 && (
              <div style={{ paddingTop: '16px', borderTop: '1px solid var(--border-glass)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                  <span style={{ fontSize: '0.88rem', fontWeight: '800', color: 'var(--text-primary)' }}>
                    Total Meal Nutrition:
                  </span>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.2rem', fontWeight: '800', color: 'var(--calorie-orange)' }}>
                      {totalKcal} kcal
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                      P: {Math.round(totalProtein)}g • C: {Math.round(totalCarbs)}g • F: {Math.round(totalFat)}g
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleSaveMeal}
                  disabled={isSaving}
                  className="btn-primary"
                  style={{ width: '100%', padding: '12px', fontSize: '0.94rem' }}
                >
                  {isSaving ? 'Recording Meal...' : `Save ${mealType.charAt(0).toUpperCase() + mealType.slice(1)} to Journal`}
                </button>
              </div>
            )}

          </div>

        </div>

      </div>

    </div>
  );
};
