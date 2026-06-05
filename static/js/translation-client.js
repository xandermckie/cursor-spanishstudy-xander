const LINGVA_BASES = [
  'https://lingva.ml/api/v1',
];

const MYMEMORY_URL = 'https://api.mymemory.translated.net/get';

function isValidTranslation(text) {
  const cleaned = (text || '').trim();
  if (!cleaned) return false;
  return !cleaned.toUpperCase().includes('MYMEMORY WARNING');
}

async function fetchLingva(text, sourceLang, targetLang) {
  const encoded = encodeURIComponent(text.slice(0, 500));
  for (const base of LINGVA_BASES) {
    try {
      const response = await fetch(
        `${base}/${sourceLang}/${targetLang}/${encoded}`,
        { headers: { Accept: 'application/json' } },
      );
      if (!response.ok) continue;
      const data = await response.json();
      const translated = (data.translation || '').trim();
      if (isValidTranslation(translated)) return translated;
    } catch (err) {
      console.warn('Lingva browser fallback failed:', base, err);
    }
  }
  return null;
}

async function fetchMyMemory(text, sourceLang, targetLang) {
  try {
    const params = new URLSearchParams({
      q: text.slice(0, 500),
      langpair: `${sourceLang}|${targetLang}`,
    });
    const response = await fetch(`${MYMEMORY_URL}?${params.toString()}`);
    if (!response.ok) return null;
    const data = await response.json();
    const translated = (data.responseData?.translatedText || '').trim();
    if (isValidTranslation(translated)) return translated;
  } catch (err) {
    console.warn('MyMemory browser fallback failed:', err);
  }
  return null;
}

/**
 * Translate directly from the browser (per-user IP quota).
 * Used when the server-side proxy fails on shared hosting IPs.
 */
export async function translateDirect(text, sourceLang, targetLang) {
  const trimmed = (text || '').trim();
  if (!trimmed || sourceLang === targetLang) return null;

  const lingva = await fetchLingva(trimmed, sourceLang, targetLang);
  if (lingva) return lingva;

  return fetchMyMemory(trimmed, sourceLang, targetLang);
}
