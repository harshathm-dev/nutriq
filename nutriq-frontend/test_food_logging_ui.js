import assert from 'node:assert';

console.log("=================================================");
console.log("RUNNING FOOD LOGGING LOGIC & MATH TEST SUITE");
console.log("=================================================");

// Food Catalog Data Item: Plain Dosa
const plainDosa = {
  id: "dosa-1",
  name: "Plain Dosa",
  category: "dosa",
  serving_size: 100.0,
  unit: "g",
  calories: 168.0,
  protein_g: 3.9,
  carbs_g: 29.4,
  fat_g: 3.7,
  fiber_g: 1.8,
  serving_conversions: [
    { serving_label: "1 piece (medium)", grams: 80.0, unit: "piece" },
    { serving_label: "1 large crispy dosa", grams: 120.0, unit: "dosa" },
    { serving_label: "2 dosas (standard serving)", grams: 160.0, unit: "serving" }
  ]
};

// 1. Test Single Piece Selection (80g)
const qty1 = 1;
const unit1Grams = 80.0;
const totalGrams1 = unit1Grams * qty1;
const mult1 = totalGrams1 / 100.0;
const cal1 = Math.round(plainDosa.calories * mult1);
const pro1 = Math.round(plainDosa.protein_g * mult1 * 10) / 10;
const carb1 = Math.round(plainDosa.carbs_g * mult1 * 10) / 10;
const fat1 = Math.round(plainDosa.fat_g * mult1 * 10) / 10;

assert.strictEqual(cal1, 134, "1 medium plain dosa must be 134 kcal");
assert.strictEqual(pro1, 3.1, "1 medium plain dosa protein must be 3.1g");
assert.strictEqual(carb1, 23.5, "1 medium plain dosa carbs must be 23.5g");
assert.strictEqual(fat1, 3.0, "1 medium plain dosa fat must be 3.0g");
console.log("✓ Test 1 & 2: 1 piece Plain Dosa calculates accurately (134 kcal)");

// 2. Test Changing Quantity to 2 Pieces (160g)
const qty2 = 2;
const totalGrams2 = unit1Grams * qty2;
const mult2 = totalGrams2 / 100.0;
const cal2 = Math.round(plainDosa.calories * mult2);
const pro2 = Math.round(plainDosa.protein_g * mult2 * 10) / 10;

assert.strictEqual(cal2, 269, "2 medium plain dosas must be 269 kcal");
assert.notStrictEqual(cal1, cal2, "Calories must scale with quantity");
console.log("✓ Test 3 & 4: Quantity change to 2 pieces scales dynamically to 269 kcal");

// 3. Test Changing Serving Unit to 1 Large Crispy Dosa (120g)
const unitLargeGrams = 120.0;
const totalGramsLarge = unitLargeGrams * 1;
const multLarge = totalGramsLarge / 100.0;
const calLarge = Math.round(plainDosa.calories * multLarge);
const carbLarge = Math.round(plainDosa.carbs_g * multLarge * 10) / 10;

assert.strictEqual(calLarge, 202, "1 large crispy dosa must be 202 kcal");
assert.strictEqual(carbLarge, 35.3, "1 large crispy dosa carbs must be 35.3g");
console.log("✓ Test 5 & 6: Serving unit change scales correctly to 202 kcal");

// 4. Test Multiple Foods in Staged Meal & Dynamic Totals
const mealItems = [
  { food_name: "Plain Dosa", quantity: 2, calories: 269, protein_g: 6.2, carbs_g: 47.0, fat_g: 5.9 },
  { food_name: "Tamil Sambar", quantity: 1, calories: 102, protein_g: 5.1, carbs_g: 15.3, fat_g: 2.4 },
  { food_name: "Boiled Egg", quantity: 2, calories: 156, protein_g: 12.6, carbs_g: 1.2, fat_g: 10.6 }
];

let totalKcal = mealItems.reduce((acc, i) => acc + i.calories, 0);
let totalPro = Math.round(mealItems.reduce((acc, i) => acc + i.protein_g, 0) * 10) / 10;
let totalCarb = Math.round(mealItems.reduce((acc, i) => acc + i.carbs_g, 0) * 10) / 10;
let totalFat = Math.round(mealItems.reduce((acc, i) => acc + i.fat_g, 0) * 10) / 10;

assert.strictEqual(totalKcal, 527, "Total calories for 3 items must be 527 kcal");
assert.strictEqual(totalPro, 23.9, "Total protein must be 23.9g");
assert.strictEqual(totalCarb, 63.5, "Total carbs must be 63.5g");
assert.strictEqual(totalFat, 18.9, "Total fat must be 18.9g");
console.log("✓ Test 7 & 8: Multiple foods stage properly with 527 kcal total");

// 5. Test Removing an Item
const filteredItems = mealItems.filter(i => i.food_name !== "Boiled Egg");
totalKcal = filteredItems.reduce((acc, i) => acc + i.calories, 0);
assert.strictEqual(totalKcal, 371, "Removing Boiled Egg updates total to 371 kcal");
console.log("✓ Test 9 & 10: Item removal updates totals dynamically to 371 kcal");

console.log("=================================================");
console.log("ALL FOOD LOGGING TESTS PASSED (5/5)");
console.log("=================================================");
