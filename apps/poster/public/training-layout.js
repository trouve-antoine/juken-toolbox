export function trainingLayout(params) {
  const columns = Number(params.get('n') ?? 6);
  if (!Number.isInteger(columns) || columns < 5 || columns > 10) throw new Error('Kanji per sheet must be from 5 to 10.');
  // A4 landscape with 10 mm margins and 1 mm of rounding clearance.
  const square = Math.floor(276 / columns * 1000) / 1000;
  const rows = Math.floor(189 / square);
  return { columns, rows, blanks: rows - 2, square };
}

export function selectedCharacters(params) {
  return [...new Set(Array.from(params.get('selected') ?? ''))];
}
