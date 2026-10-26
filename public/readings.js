// Preserve MEXT order within each category; neither category is a frequency rank.
export function posterReadings(readings, level, showAll = false) {
  const selected = readings
    .filter(reading => level === 'all' || reading.level?.startsWith(level[0]))
    .sort((a, b) => Number(a.specialOrNarrowUse) - Number(b.specialOrNarrowUse)
      || a.mextOrder - b.mextOrder);
  return showAll ? selected : selected.slice(0, 3);
}
