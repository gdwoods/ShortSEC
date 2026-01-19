// utils/countryToFlag.ts

export type CountryInfo = {
  flag: string;
  isRisky: boolean;
};

export function countryInfo(country?: string | null): CountryInfo {
  if (!country) return { flag: "", isRisky: false };

  // Normalize name
  const name = country.trim().toUpperCase();

  // ✅ Aliases & cleanup - Common country name variations found in SEC filings
  const aliases: Record<string, string> = {
    // United States
    USA: "US",
    "UNITED STATES": "US",
    "UNITED STATES OF AMERICA": "US",
    "U.S.": "US",
    "U.S.A.": "US",
    "U.S.A": "US",

    // United Kingdom / Great Britain
    UK: "GB",
    ENGLAND: "GB",
    BRITAIN: "GB",
    "UNITED KINGDOM": "GB",
    "GREAT BRITAIN": "GB",
    "U.K.": "GB",

    // Hong Kong
    HONGKONG: "HK",
    "HONG KONG": "HK",

    // Korea
    KOREA: "KR",
    "SOUTH KOREA": "KR",
    "REPUBLIC OF KOREA": "KR",
    "NORTH KOREA": "KP",
    "DEMOCRATIC PEOPLE'S REPUBLIC OF KOREA": "KP",

    // Russia
    RUSSIA: "RU",
    "RUSSIAN FEDERATION": "RU",

    // China
    CHINA: "CN",
    PRC: "CN",
    "PEOPLE'S REPUBLIC OF CHINA": "CN",
    "REPUBLIC OF CHINA": "CN",

    // Caribbean / Offshore
    CAYMAN: "KY",
    "CAYMAN ISLANDS": "KY",
    BERMUDA: "BM",
    "BRITISH VIRGIN ISLANDS": "VG",
    "VIRGIN ISLANDS": "VG",
    "BVI": "VG",
    BARBADOS: "BB",
    PANAMA: "PA",
    "REPUBLIC OF PANAMA": "PA",
    "MARSHALL ISLANDS": "MH",
    "REPUBLIC OF THE MARSHALL ISLANDS": "MH",

    // Asia Pacific
    TAIWAN: "TW",
    "TAIWAN, PROVINCE OF CHINA": "TW",
    SINGAPORE: "SG",
    "REPUBLIC OF SINGAPORE": "SG",
    MALAYSIA: "MY",
    INDONESIA: "ID",
    "REPUBLIC OF INDONESIA": "ID",
    THAILAND: "TH",
    "KINGDOM OF THAILAND": "TH",
    INDIA: "IN",
    "REPUBLIC OF INDIA": "IN",
    AUSTRALIA: "AU",
    "COMMONWEALTH OF AUSTRALIA": "AU",
    JAPAN: "JP",
    "NEW ZEALAND": "NZ",
    PHILIPPINES: "PH",
    "REPUBLIC OF THE PHILIPPINES": "PH",
    VIETNAM: "VN",
    "SOCIALIST REPUBLIC OF VIETNAM": "VN",
    "SOUTH VIETNAM": "VN",

    // Middle East
    ISRAEL: "IL",
    "STATE OF ISRAEL": "IL",
    "UNITED ARAB EMIRATES": "AE",
    UAE: "AE",
    SAUDI: "SA",
    "SAUDI ARABIA": "SA",
    "KINGDOM OF SAUDI ARABIA": "SA",

    // Europe
    CANADA: "CA",
    GERMANY: "DE",
    "FEDERAL REPUBLIC OF GERMANY": "DE",
    FRANCE: "FR",
    "FRENCH REPUBLIC": "FR",
    ITALY: "IT",
    "ITALIAN REPUBLIC": "IT",
    SPAIN: "ES",
    "KINGDOM OF SPAIN": "ES",
    NETHERLANDS: "NL",
    "KINGDOM OF THE NETHERLANDS": "NL",
    BELGIUM: "BE",
    "KINGDOM OF BELGIUM": "BE",
    SWITZERLAND: "CH",
    "SWISS CONFEDERATION": "CH",
    SWEDEN: "SE",
    "KINGDOM OF SWEDEN": "SE",
    NORWAY: "NO",
    "KINGDOM OF NORWAY": "NO",
    DENMARK: "DK",
    "KINGDOM OF DENMARK": "DK",
    FINLAND: "FI",
    "REPUBLIC OF FINLAND": "FI",
    POLAND: "PL",
    "REPUBLIC OF POLAND": "PL",
    IRELAND: "IE",
    "REPUBLIC OF IRELAND": "IE",
    PORTUGAL: "PT",
    "PORTUGUESE REPUBLIC": "PT",
    GREECE: "GR",
    "HELLENIC REPUBLIC": "GR",
    AUSTRIA: "AT",
    "REPUBLIC OF AUSTRIA": "AT",

    // Americas
    MEXICO: "MX",
    "UNITED MEXICAN STATES": "MX",
    BRAZIL: "BR",
    "FEDERATIVE REPUBLIC OF BRAZIL": "BR",
    ARGENTINA: "AR",
    "ARGENTINE REPUBLIC": "AR",
    CHILE: "CL",
    "REPUBLIC OF CHILE": "CL",
    COLOMBIA: "CO",
    "REPUBLIC OF COLOMBIA": "CO",
    PERU: "PE",
    "REPUBLIC OF PERU": "PE",

    // Africa
    "SOUTH AFRICA": "ZA",
    "REPUBLIC OF SOUTH AFRICA": "ZA",
    EGYPT: "EG",
    "ARAB REPUBLIC OF EGYPT": "EG",
    NIGERIA: "NG",
    "FEDERAL REPUBLIC OF NIGERIA": "NG",

    // Other common variations
    "COTE D'IVOIRE": "CI",
    "IVORY COAST": "CI",
    "REPUBLIC OF KOREA": "KR",
    "DEMOCRATIC REPUBLIC OF THE CONGO": "CD",
    "DR CONGO": "CD",
    "D.R. CONGO": "CD",
    "CONGO (DEMOCRATIC REPUBLIC)": "CD",
  };

  const code =
    aliases[name] ||
    (name.length === 2 ? name : null);

  if (!code) return { flag: "", isRisky: false };

  // Convert ISO → flag emoji
  const flag = code
    .toUpperCase()
    .replace(/./g, (char) =>
      String.fromCodePoint(127397 + char.charCodeAt(0))
    );

  // ✅ Risky jurisdictions
  const RISKY = new Set([
    "CN", // China
    "HK", // Hong Kong
    "MY", // Malaysia
    "SG", // Singapore
    "KY", // Cayman Islands
    "VG", // British Virgin Islands
    "BM", // Bermuda
    "MH", // Marshall Islands
    "PA", // Panama
    "RU", // Russia
  ]);

  return { flag, isRisky: RISKY.has(code) };
}

// ✅ Named export (for backward compatibility)
export function countryToFlag(country?: string | null): string {
  return countryInfo(country).flag;
}
