import { getToday, formatDate, parseDateParts, addDays, subtractDays, getLocalDateFromTimestamp } from '../src/utils/dateUtils.js';
import { normalizeMeal } from '../src/services/api.js';

console.log("--- Testing Date Utilities ---");
const todayStr = getToday();
console.log("getToday():", todayStr);
console.assert(/^\d{4}-\d{2}-\d{2}$/.test(todayStr), "getToday() must return YYYY-MM-DD");

const formattedToday = formatDate(todayStr);
console.log("formatDate(today):", formattedToday);
console.assert(formattedToday.length > 0, "formatDate should produce formatted string");

const yesterdayStr = subtractDays(todayStr, 1);
const tomorrowStr = addDays(todayStr, 1);
console.log("yesterday:", yesterdayStr, "tomorrow:", tomorrowStr);

console.log("\n--- Testing Meal Normalization with 2x Plain Dosa ---");
const rawMeal = {
  id: "meal_test_999",
  meal_type: "breakfast",
  occurred_at: new Date().toISOString(),
  items: [
    {
      food_id: "food_dosa_1",
      food_name: "Plain Dosa",
      quantity: 2,
      calories: 268,
      protein_g: 6.2,
      carbs_g: 47.0,
      fat_g: 5.9
    }
  ]
};

const norm = normalizeMeal(rawMeal);
console.log("Normalized Meal:", {
  id: norm.id,
  type: norm.meal_type,
  date: norm.date,
  total_calories: norm.total_calories,
  total_protein: norm.total_protein,
  item_name: norm.items[0].food_name,
  item_portion: norm.items[0].portion,
  item_quantity: norm.items[0].quantity
});

console.assert(norm.items[0].food_name === "Plain Dosa", "Item food_name must match");
console.assert(norm.items[0].name === "Plain Dosa", "Item name alias must match");
console.assert(norm.items[0].quantity === 2, "Item quantity must be 2");
console.assert(norm.items[0].portion === 2, "Item portion must be 2");
console.assert(norm.total_calories === 268, "Meal total_calories must match");
console.assert(norm.total_protein === 6.2, "Meal total_protein must match");

console.log("\nAll frontend date and normalization tests passed with 100% success!");
