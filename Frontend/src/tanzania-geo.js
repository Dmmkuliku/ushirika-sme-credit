/**
 * Tanzania administrative geography: 31 regions and their districts.
 * Used for cascading Region → District selects.
 */

export const TANZANIA_REGIONS = [
  'Arusha',
  'Dar es Salaam',
  'Dodoma',
  'Geita',
  'Iringa',
  'Kagera',
  'Katavi',
  'Kigoma',
  'Kilimanjaro',
  'Lindi',
  'Manyara',
  'Mara',
  'Mbeya',
  'Morogoro',
  'Mtwara',
  'Mwanza',
  'Njombe',
  'Pwani',
  'Rukwa',
  'Ruvuma',
  'Shinyanga',
  'Simiyu',
  'Singida',
  'Songwe',
  'Tabora',
  'Tanga',
  'Kaskazini Unguja',
  'Kusini Unguja',
  'Mjini Magharibi',
  'Kaskazini Pemba',
  'Kusini Pemba',
];

export const DISTRICTS_BY_REGION = {
  Arusha: ['Arusha City', 'Arusha District', 'Karatu', 'Longido', 'Meru', 'Monduli', 'Ngorongoro'],
  'Dar es Salaam': ['Ilala', 'Kinondoni', 'Temeke', 'Ubungo', 'Kigamboni'],
  Dodoma: ['Bahi', 'Chamwino', 'Chemba', 'Dodoma City', 'Kondoa', 'Kongwa', 'Mpwapwa'],
  Geita: ['Bukombe', 'Chato', 'Geita', 'Mbogwe', "Nyang'hwale"],
  Iringa: ['Iringa District', 'Iringa Municipal', 'Kilolo', 'Mufindi'],
  Kagera: ['Biharamulo', 'Bukoba District', 'Bukoba Municipal', 'Karagwe', 'Kyerwa', 'Missenyi', 'Muleba', 'Ngara'],
  Katavi: ['Mlele', 'Mpanda District', 'Mpanda Town', 'Nsimbo', 'Tanganyika'],
  Kigoma: ['Buhigwe', 'Kakonko', 'Kasulu District', 'Kasulu Town', 'Kibondo', 'Kigoma District', 'Kigoma-Ujiji Municipal', 'Uvinza'],
  Kilimanjaro: ['Hai', 'Moshi District', 'Moshi Municipal', 'Mwanga', 'Rombo', 'Same', 'Siha'],
  Lindi: ['Kilwa', 'Lindi District', 'Lindi Municipal', 'Liwale', 'Nachingwea', 'Ruangwa'],
  Manyara: ['Babati District', 'Babati Town', 'Hanang', 'Kiteto', 'Mbulu District', 'Mbulu Town', 'Simanjiro'],
  Mara: ['Bunda District', 'Bunda Town', 'Butiama', 'Musoma District', 'Musoma Municipal', 'Rorya', 'Serengeti', 'Tarime District', 'Tarime Town'],
  Mbeya: ['Busokelo', 'Chunya', 'Kyela', 'Mbarali', 'Mbeya City', 'Mbeya District', 'Rungwe'],
  Morogoro: ['Gairo', 'Ifakara Town', 'Kilombero', 'Kilosa', 'Malinyi', 'Morogoro District', 'Morogoro Municipal', 'Mvomero', 'Ulanga'],
  Mtwara: ['Masasi District', 'Masasi Town', 'Mtwara District', 'Mtwara Municipal', 'Nanyumbu', 'Newala District', 'Newala Town', 'Tandahimba'],
  Mwanza: ['Buchosa', 'Ilemela', 'Kwimba', 'Magu', 'Misungwi', 'Nyamagana', 'Sengerema', 'Ukerewe'],
  Njombe: ['Ludewa', 'Makambako Town', 'Makete', 'Njombe District', 'Njombe Town', "Wanging'ombe"],
  Pwani: ['Bagamoyo', 'Chalinze', 'Kibaha District', 'Kibaha Town', 'Kisarawe', 'Mafia', 'Mkuranga', 'Rufiji'],
  Rukwa: ['Kalambo', 'Nkasi', 'Sumbawanga District', 'Sumbawanga Municipal'],
  Ruvuma: ['Mbinga District', 'Mbinga Town', 'Namtumbo', 'Nyasa', 'Songea District', 'Songea Municipal', 'Tunduru'],
  Shinyanga: ['Kahama Town', 'Kishapu', 'Msalala', 'Shinyanga District', 'Shinyanga Municipal', 'Ushetu'],
  Simiyu: ['Bariadi District', 'Bariadi Town', 'Busega', 'Itilima', 'Maswa', 'Meatu'],
  Singida: ['Ikungi', 'Iramba', 'Manyoni', 'Mkalama', 'Singida District', 'Singida Municipal'],
  Songwe: ['Ileje', 'Mbozi', 'Momba', 'Songwe', 'Tunduma Town'],
  Tabora: ['Igunga', 'Kaliua', 'Nzega District', 'Nzega Town', 'Sikonge', 'Tabora Municipal', 'Urambo', 'Uyui'],
  Tanga: ['Handeni District', 'Handeni Town', 'Kilindi', 'Korogwe District', 'Korogwe Town', 'Lushoto', 'Muheza', 'Mkinga', 'Pangani', 'Tanga City'],
  'Kaskazini Unguja': ['Kaskazini A', 'Kaskazini B'],
  'Kusini Unguja': ['Kati', 'Kusini'],
  'Mjini Magharibi': ['Magharibi A', 'Magharibi B', 'Mjini'],
  'Kaskazini Pemba': ['Micheweni', 'Wete'],
  'Kusini Pemba': ['Chake Chake', 'Mkoani'],
};

export function isTanzaniaRegion(value) {
  return TANZANIA_REGIONS.includes(String(value || '').trim());
}

export function districtsForRegion(region) {
  return DISTRICTS_BY_REGION[String(region || '').trim()] || [];
}

export function isDistrictInRegion(region, district) {
  return districtsForRegion(region).includes(String(district || '').trim());
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

export function regionSelectHtml({
  id = 'location',
  name = 'location',
  value = '',
  required = true,
  placeholder = 'Select region',
} = {}) {
  const selected = String(value || '').trim();
  const options = [...TANZANIA_REGIONS];
  if (selected && !options.includes(selected)) options.unshift(selected);
  const opts = [
    `<option value="">${escapeHtml(placeholder)}</option>`,
    ...options.map((region) => {
      const isSelected = region === selected ? ' selected' : '';
      return `<option value="${escapeHtml(region)}"${isSelected}>${escapeHtml(region)}</option>`;
    }),
  ].join('');
  return `<select id="${escapeHtml(id)}" name="${escapeHtml(name)}"${required ? ' required' : ''}>${opts}</select>`;
}

export function districtSelectHtml({
  id = 'district',
  name = 'district',
  region = '',
  value = '',
  required = true,
  placeholder = 'Select district',
} = {}) {
  const selected = String(value || '').trim();
  const districts = [...districtsForRegion(region)];
  if (selected && !districts.includes(selected)) districts.unshift(selected);
  const disabled = !region ? ' disabled' : '';
  const opts = [
    `<option value="">${escapeHtml(placeholder)}</option>`,
    ...districts.map((district) => {
      const isSelected = district === selected ? ' selected' : '';
      return `<option value="${escapeHtml(district)}"${isSelected}>${escapeHtml(district)}</option>`;
    }),
  ].join('');
  return `<select id="${escapeHtml(id)}" name="${escapeHtml(name)}"${required ? ' required' : ''}${disabled}>${opts}</select>`;
}

/** Keep district options in sync when the region changes. */
export function bindRegionDistrictCascade({
  regionSelect,
  districtSelect,
  placeholder = 'Select district',
} = {}) {
  if (!regionSelect || !districtSelect) return;

  const refresh = () => {
    const region = regionSelect.value;
    const previous = districtSelect.value;
    const districts = districtsForRegion(region);
    districtSelect.disabled = !region;
    districtSelect.innerHTML = [
      `<option value="">${escapeHtml(placeholder)}</option>`,
      ...districts.map((d) => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`),
    ].join('');
    if (districts.includes(previous)) districtSelect.value = previous;
    else districtSelect.value = '';
    districtSelect.dispatchEvent(new Event('change'));
  };

  regionSelect.addEventListener('change', refresh);
}
