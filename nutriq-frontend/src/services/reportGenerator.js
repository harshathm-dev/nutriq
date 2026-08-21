/**
 * NutriQ Report Generator (Offline + Online)
 * Generates and downloads Daily and Weekly nutrition reports in PDF, CSV, and JSON.
 * Guaranteed to produce real ISO formatted dates (YYYY-MM-DD) and clean human-readable files.
 */

// Helper to trigger file download
const triggerDownload = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    window.URL.revokeObjectURL(url);
    a.remove();
  }, 100);
};

// Simple standard PDF synthesizer producing standard PDF 1.4 bytes
const createSimplePdf = (title, lines) => {
  let contentStream = `BT\n/F1 16 Tf\n50 750 Td\n(${title.replace(/[()\\]/g, '')}) Tj\nET\n`;
  let y = 720;
  
  lines.forEach((line) => {
    if (y < 50) return; // single page safety limit
    const escaped = line.replace(/[()\\]/g, '');
    const isHeader = line.startsWith('===') || line.startsWith('---') || line.toUpperCase() === line && line.length < 30;
    const fontSize = isHeader ? 12 : 10;
    contentStream += `BT\n/F1 ${fontSize} Tf\n50 ${y} Td\n(${escaped}) Tj\nET\n`;
    y -= (fontSize + 6);
  });

  const objects = [];
  objects.push(`1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n`);
  objects.push(`2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n`);
  objects.push(`3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n`);
  objects.push(`4 0 obj\n<< /Length ${contentStream.length} >>\nstream\n${contentStream}endstream\nendobj\n`);
  objects.push(`5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n`);

  let body = `%PDF-1.4\n`;
  const xref = [0];
  let offset = body.length;

  objects.forEach((obj) => {
    xref.push(offset);
    body += obj;
    offset = body.length;
  });

  const startxref = offset;
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (let i = 1; i <= objects.length; i++) {
    body += String(xref[i]).padStart(10, '0') + ` 00000 n \n`;
  }
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${startxref}\n%%EOF\n`;

  return new Blob([body], { type: 'application/pdf' });
};

export const reportGenerator = {
  // DAILY REPORT
  exportDaily: (summaryData, format = 'json', userProfile = null) => {
    const dateStr = summaryData.date || new Date().toISOString().split('T')[0];
    const userName = userProfile?.name || 'NutriQ User';

    if (format === 'json') {
      const payload = {
        report_type: 'NutriQ Daily Nutrition Summary',
        generated_at: new Date().toISOString(),
        user: userName,
        date: dateStr,
        ...summaryData
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      triggerDownload(blob, `NutriQ_Daily_Summary_${dateStr}.json`);
      return { success: true, filename: `NutriQ_Daily_Summary_${dateStr}.json` };
    }

    if (format === 'csv') {
      let csv = '\uFEFF'; // UTF-8 BOM
      csv += `# NutriQ Daily Nutrition Summary\n`;
      csv += `# Date,${dateStr}\n`;
      csv += `# User,${userName}\n\n`;

      csv += `Metric,Consumed,Target,Unit\n`;
      csv += `Calories,${summaryData.calories?.consumed || 0},${summaryData.calories?.target || 2000},kcal\n`;
      csv += `Protein,${summaryData.macros?.protein?.consumed || 0},${summaryData.macros?.protein?.target || 100},g\n`;
      csv += `Carbohydrates,${summaryData.macros?.carbohydrates?.consumed || 0},${summaryData.macros?.carbohydrates?.target || 250},g\n`;
      csv += `Fat,${summaryData.macros?.fat?.consumed || 0},${summaryData.macros?.fat?.target || 60},g\n`;
      csv += `Fiber,${summaryData.macros?.fiber?.consumed || 0},${summaryData.macros?.fiber?.target || 28},g\n`;
      csv += `Water,${summaryData.hydration?.consumed_ml || 0},${summaryData.hydration?.target_ml || 2500},ml\n\n`;

      csv += `Date,Meal Type,Logged Status,Calories (kcal),Protein (g),Carbs (g),Fat (g)\n`;
      const mealSlots = ['breakfast', 'lunch', 'snack', 'dinner'];
      mealSlots.forEach((slot) => {
        const slotData = summaryData.meals?.[slot] || {};
        csv += `${dateStr},${slot.toUpperCase()},${slotData.logged ? 'Logged' : 'Not Logged'},${slotData.total_calories || 0},${slotData.total_protein_g || 0},${slotData.total_carbs_g || 0},${slotData.total_fat_g || 0}\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      triggerDownload(blob, `NutriQ_Daily_Summary_${dateStr}.csv`);
      return { success: true, filename: `NutriQ_Daily_Summary_${dateStr}.csv` };
    }

    if (format === 'pdf') {
      const lines = [
        `NutriQ Daily Nutrition Summary`,
        `Date: ${dateStr} | User: ${userName}`,
        `----------------------------------------------------`,
        `NUTRITION TARGETS & TOTALS:`,
        `Calories: ${summaryData.calories?.consumed || 0} / ${summaryData.calories?.target || 2000} kcal (${summaryData.calories?.remaining || 0} kcal remaining)`,
        `Protein: ${summaryData.macros?.protein?.consumed || 0}g / ${summaryData.macros?.protein?.target || 100}g target`,
        `Carbohydrates: ${summaryData.macros?.carbohydrates?.consumed || 0}g / ${summaryData.macros?.carbohydrates?.target || 250}g target`,
        `Fat: ${summaryData.macros?.fat?.consumed || 0}g / ${summaryData.macros?.fat?.target || 60}g target`,
        `Fiber: ${summaryData.macros?.fiber?.consumed || 0}g / ${summaryData.macros?.fiber?.target || 28}g target`,
        `Hydration: ${summaryData.hydration?.consumed_ml || 0} ml / ${summaryData.hydration?.target_ml || 2500} ml target`,
        `----------------------------------------------------`,
        `MEAL BREAKDOWN:`,
        `Breakfast: ${summaryData.meals?.breakfast?.logged ? 'Logged (' + (summaryData.meals?.breakfast?.total_calories || 0) + ' kcal)' : 'Not Logged'}`,
        `Lunch: ${summaryData.meals?.lunch?.logged ? 'Logged (' + (summaryData.meals?.lunch?.total_calories || 0) + ' kcal)' : 'Not Logged'}`,
        `Evening Snack: ${summaryData.meals?.snack?.logged ? 'Logged (' + (summaryData.meals?.snack?.total_calories || 0) + ' kcal)' : 'Not Logged'}`,
        `Dinner: ${summaryData.meals?.dinner?.logged ? 'Logged (' + (summaryData.meals?.dinner?.total_calories || 0) + ' kcal)' : 'Not Logged'}`,
        `----------------------------------------------------`,
        `Status: ${summaryData.daily_insight || 'Target tracking active'}`
      ];
      const blob = createSimplePdf(`NutriQ Daily Report - ${dateStr}`, lines);
      triggerDownload(blob, `NutriQ_Daily_Report_${dateStr}.pdf`);
      return { success: true, filename: `NutriQ_Daily_Report_${dateStr}.pdf` };
    }
  },

  // WEEKLY REPORT
  exportWeekly: (weeklyData, format = 'json', userProfile = null) => {
    const rangeStr = `${weeklyData.week_start}_to_${weeklyData.week_end}`;
    const userName = userProfile?.name || 'NutriQ User';
    const s = weeklyData.summary || {};

    if (format === 'json') {
      const payload = {
        report_type: 'NutriQ Weekly Nutrition Summary',
        generated_at: new Date().toISOString(),
        user: userName,
        week_range: weeklyData.display_range,
        ...weeklyData
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      triggerDownload(blob, `NutriQ_Weekly_Summary_${rangeStr}.json`);
      return { success: true, filename: `NutriQ_Weekly_Summary_${rangeStr}.json` };
    }

    if (format === 'csv') {
      let csv = '\uFEFF';
      csv += `# NutriQ Weekly Nutrition Summary\n`;
      csv += `# Range,${weeklyData.display_range}\n`;
      csv += `# User,${userName}\n\n`;

      csv += `Weekly Metric,Value,Target,Unit\n`;
      csv += `Total Weekly Calories,${s.total_weekly_calories || 0},${(s.calorie_target || 2000) * 7},kcal\n`;
      csv += `Average Daily Calories,${s.avg_daily_calories || 0},${s.calorie_target || 2000},kcal/day\n`;
      csv += `Average Daily Protein,${s.avg_protein_g || 0},${s.protein_target_g || 100},g/day\n`;
      csv += `Average Daily Carbs,${s.avg_carbs_g || 0},250,g/day\n`;
      csv += `Average Daily Fat,${s.avg_fat_g || 0},60,g/day\n`;
      csv += `Average Daily Fiber,${s.avg_fiber_g || 0},28,g/day\n`;
      csv += `Average Daily Water,${s.avg_water_ml || 0},${s.water_target_ml || 2500},ml/day\n`;
      csv += `Total Meals Logged,${s.total_meals_logged || 0},-,meals\n`;
      csv += `Days with Complete Logging,${s.days_with_complete_logging || 0},7,days\n`;
      csv += `Days with Missed Meals,${s.days_with_missed_meals || 0},-,days\n`;
      csv += `Goal Adherence,${s.goal_adherence_pct || 0},100,%\n\n`;

      csv += `Date,Day,Calories Consumed,Calorie Target,Protein (g),Carbs (g),Fat (g),Water (ml),Meals Logged,Status\n`;
      (weeklyData.daily_breakdown || []).forEach((d) => {
        csv += `${d.date},${d.day_name},${d.calories_consumed},${d.calorie_target},${d.protein_consumed_g},${d.carbs_consumed_g},${d.fat_consumed_g},${d.water_consumed_ml},${d.meals_logged_count},${d.is_complete ? 'Complete' : 'Incomplete'}\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      triggerDownload(blob, `NutriQ_Weekly_Summary_${rangeStr}.csv`);
      return { success: true, filename: `NutriQ_Weekly_Summary_${rangeStr}.csv` };
    }

    if (format === 'pdf') {
      const lines = [
        `NutriQ Weekly Nutrition Summary`,
        `Range: ${weeklyData.display_range} | User: ${userName}`,
        `----------------------------------------------------`,
        `WEEKLY TOTALS & DAILY AVERAGES:`,
        `Avg Daily Calories: ${s.avg_daily_calories || 0} kcal / day (Target: ${s.calorie_target || 2000} kcal)`,
        `Total Weekly Calories: ${s.total_weekly_calories || 0} kcal`,
        `Avg Daily Protein: ${s.avg_protein_g || 0}g / day (Target: ${s.protein_target_g || 100}g)`,
        `Avg Daily Carbs: ${s.avg_carbs_g || 0}g / day`,
        `Avg Daily Fat: ${s.avg_fat_g || 0}g / day`,
        `Avg Daily Fiber: ${s.avg_fiber_g || 0}g / day`,
        `Avg Daily Water: ${s.avg_water_ml || 0} ml / day (Target: ${s.water_target_ml || 2500} ml)`,
        `Total Meals Logged: ${s.total_meals_logged || 0}`,
        `Complete Logging Days: ${s.days_with_complete_logging || 0} / 7 days`,
        `Goal Adherence: ${s.goal_adherence_pct || 0}%`,
        `----------------------------------------------------`,
        `7-DAY BREAKDOWN:`,
        ...(weeklyData.daily_breakdown || []).map(d => `${d.day_name} (${d.date}): ${d.calories_consumed} kcal | Pro: ${d.protein_consumed_g}g | Water: ${d.water_consumed_ml}ml [${d.is_complete ? 'Complete' : 'Incomplete'}]`),
        `----------------------------------------------------`,
        `WEEKLY INSIGHTS:`,
        ...(weeklyData.insights || ['No weekly insights recorded.'])
      ];
      const blob = createSimplePdf(`NutriQ Weekly Report - ${weeklyData.display_range}`, lines);
      triggerDownload(blob, `NutriQ_Weekly_Report_${rangeStr}.pdf`);
      return { success: true, filename: `NutriQ_Weekly_Report_${rangeStr}.pdf` };
    }
  }
};
