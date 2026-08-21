import assert from 'node:assert';
import { isProfileComplete, isPublicPath, pathToTab, tabToPath } from './src/store/useStore.js';

console.log("=================================================");
console.log("RUNNING FRONTEND UNIT & ROUTE LOGIC VALIDATION");
console.log("=================================================");

// 1. Test isPublicPath
assert.strictEqual(isPublicPath('/'), true, "Root route '/' should be public");
assert.strictEqual(isPublicPath('/welcome'), true, "Route '/welcome' should be public");
assert.strictEqual(isPublicPath('/login'), true, "Route '/login' should be public");
assert.strictEqual(isPublicPath('/register'), true, "Route '/register' should be public");
assert.strictEqual(isPublicPath('/dashboard'), false, "Route '/dashboard' must NOT be public");
assert.strictEqual(isPublicPath('/profile-setup'), false, "Route '/profile-setup' must NOT be public");
assert.strictEqual(isPublicPath('/ai-assistant'), false, "Route '/ai-assistant' must NOT be public");
assert.strictEqual(isPublicPath('/analytics'), false, "Route '/analytics' must NOT be public");
console.log("✓ Test 1: Public route classifications pass");

// 2. Test pathToTab & tabToPath
assert.strictEqual(pathToTab('/'), 'welcome');
assert.strictEqual(pathToTab('/welcome'), 'welcome');
assert.strictEqual(pathToTab('/login'), 'login');
assert.strictEqual(pathToTab('/register'), 'register');
assert.strictEqual(pathToTab('/dashboard'), 'dashboard');
assert.strictEqual(pathToTab('/profile-setup'), 'onboarding');
assert.strictEqual(pathToTab('/log-meal'), 'add_food');
assert.strictEqual(pathToTab('/food-catalog'), 'search');
assert.strictEqual(pathToTab('/meal-planner'), 'planner');
assert.strictEqual(pathToTab('/ai-assistant'), 'assistant');
assert.strictEqual(pathToTab('/analytics'), 'analytics');
assert.strictEqual(pathToTab('/family-profiles'), 'family');
assert.strictEqual(pathToTab('/settings'), 'settings');

assert.strictEqual(tabToPath('welcome'), '/welcome');
assert.strictEqual(tabToPath('login'), '/login');
assert.strictEqual(tabToPath('register'), '/register');
assert.strictEqual(tabToPath('dashboard'), '/dashboard');
assert.strictEqual(tabToPath('onboarding'), '/profile-setup');
assert.strictEqual(tabToPath('add_food'), '/log-meal');
assert.strictEqual(tabToPath('search'), '/food-catalog');
console.log("✓ Test 2: URL to Tab bidirectional mappings pass");

// 3. Test isProfileComplete with various edge cases
assert.strictEqual(isProfileComplete(null), false, "Null profile must be incomplete");
assert.strictEqual(isProfileComplete(undefined), false, "Undefined profile must be incomplete");
assert.strictEqual(isProfileComplete({}), false, "Empty profile object must be incomplete");

// Missing age
assert.strictEqual(isProfileComplete({
  name: "John",
  gender: "male",
  height_cm: 180,
  weight_kg: 75,
  activity_level: "moderately_active",
  fitness_goal: "maintain"
}), false, "Profile missing age must be incomplete");

// Missing height
assert.strictEqual(isProfileComplete({
  name: "John",
  age: 25,
  gender: "male",
  weight_kg: 75,
  activity_level: "moderately_active",
  fitness_goal: "maintain"
}), false, "Profile missing height must be incomplete");

// Missing weight
assert.strictEqual(isProfileComplete({
  name: "John",
  age: 25,
  gender: "male",
  height_cm: 180,
  activity_level: "moderately_active",
  fitness_goal: "maintain"
}), false, "Profile missing weight must be incomplete");

// Missing name
assert.strictEqual(isProfileComplete({
  name: "   ",
  age: 25,
  gender: "male",
  height_cm: 180,
  weight_kg: 75,
  activity_level: "moderately_active",
  fitness_goal: "maintain"
}), false, "Profile with blank name must be incomplete");

// Missing activity_level
assert.strictEqual(isProfileComplete({
  name: "John",
  age: 25,
  gender: "male",
  height_cm: 180,
  weight_kg: 75,
  activity_level: "",
  fitness_goal: "maintain"
}), false, "Profile with missing activity_level must be incomplete");

// Missing fitness_goal
assert.strictEqual(isProfileComplete({
  name: "John",
  age: 25,
  gender: "male",
  height_cm: 180,
  weight_kg: 75,
  activity_level: "moderately_active",
  fitness_goal: ""
}), false, "Profile with missing fitness_goal must be incomplete");

// Complete Profile
const completeProfile = {
  name: "Elena Rostova",
  age: 27,
  gender: "female",
  height_cm: 168,
  weight_kg: 60,
  activity_level: "moderately_active",
  fitness_goal: "weight_loss",
  dietary_preference: "standard",
  food_preferences: "High protein"
};
assert.strictEqual(isProfileComplete(completeProfile), true, "Complete profile must evaluate to true");
console.log("✓ Test 3: isProfileComplete deterministic logic passes all test cases");

console.log("=================================================");
console.log("ALL FRONTEND TESTS PASSED SUCCESSFULLY (3/3)");
console.log("=================================================");
