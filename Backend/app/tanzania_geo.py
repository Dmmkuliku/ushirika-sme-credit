"""Tanzania administrative geography: regions and districts."""

TANZANIA_REGIONS = {
    "Arusha",
    "Dar es Salaam",
    "Dodoma",
    "Geita",
    "Iringa",
    "Kagera",
    "Katavi",
    "Kigoma",
    "Kilimanjaro",
    "Lindi",
    "Manyara",
    "Mara",
    "Mbeya",
    "Morogoro",
    "Mtwara",
    "Mwanza",
    "Njombe",
    "Pwani",
    "Rukwa",
    "Ruvuma",
    "Shinyanga",
    "Simiyu",
    "Singida",
    "Songwe",
    "Tabora",
    "Tanga",
    "Kaskazini Unguja",
    "Kusini Unguja",
    "Mjini Magharibi",
    "Kaskazini Pemba",
    "Kusini Pemba",
}

DISTRICTS_BY_REGION = {
    "Arusha": ["Arusha City", "Arusha District", "Karatu", "Longido", "Meru", "Monduli", "Ngorongoro"],
    "Dar es Salaam": ["Ilala", "Kinondoni", "Temeke", "Ubungo", "Kigamboni"],
    "Dodoma": ["Bahi", "Chamwino", "Chemba", "Dodoma City", "Kondoa", "Kongwa", "Mpwapwa"],
    "Geita": ["Bukombe", "Chato", "Geita", "Mbogwe", "Nyang'hwale"],
    "Iringa": ["Iringa District", "Iringa Municipal", "Kilolo", "Mufindi"],
    "Kagera": ["Biharamulo", "Bukoba District", "Bukoba Municipal", "Karagwe", "Kyerwa", "Missenyi", "Muleba", "Ngara"],
    "Katavi": ["Mlele", "Mpanda District", "Mpanda Town", "Nsimbo", "Tanganyika"],
    "Kigoma": ["Buhigwe", "Kakonko", "Kasulu District", "Kasulu Town", "Kibondo", "Kigoma District", "Kigoma-Ujiji Municipal", "Uvinza"],
    "Kilimanjaro": ["Hai", "Moshi District", "Moshi Municipal", "Mwanga", "Rombo", "Same", "Siha"],
    "Lindi": ["Kilwa", "Lindi District", "Lindi Municipal", "Liwale", "Nachingwea", "Ruangwa"],
    "Manyara": ["Babati District", "Babati Town", "Hanang", "Kiteto", "Mbulu District", "Mbulu Town", "Simanjiro"],
    "Mara": ["Bunda District", "Bunda Town", "Butiama", "Musoma District", "Musoma Municipal", "Rorya", "Serengeti", "Tarime District", "Tarime Town"],
    "Mbeya": ["Busokelo", "Chunya", "Kyela", "Mbarali", "Mbeya City", "Mbeya District", "Rungwe"],
    "Morogoro": ["Gairo", "Ifakara Town", "Kilombero", "Kilosa", "Malinyi", "Morogoro District", "Morogoro Municipal", "Mvomero", "Ulanga"],
    "Mtwara": ["Masasi District", "Masasi Town", "Mtwara District", "Mtwara Municipal", "Nanyumbu", "Newala District", "Newala Town", "Tandahimba"],
    "Mwanza": ["Buchosa", "Ilemela", "Kwimba", "Magu", "Misungwi", "Nyamagana", "Sengerema", "Ukerewe"],
    "Njombe": ["Ludewa", "Makambako Town", "Makete", "Njombe District", "Njombe Town", "Wanging'ombe"],
    "Pwani": ["Bagamoyo", "Chalinze", "Kibaha District", "Kibaha Town", "Kisarawe", "Mafia", "Mkuranga", "Rufiji"],
    "Rukwa": ["Kalambo", "Nkasi", "Sumbawanga District", "Sumbawanga Municipal"],
    "Ruvuma": ["Mbinga District", "Mbinga Town", "Namtumbo", "Nyasa", "Songea District", "Songea Municipal", "Tunduru"],
    "Shinyanga": ["Kahama Town", "Kishapu", "Msalala", "Shinyanga District", "Shinyanga Municipal", "Ushetu"],
    "Simiyu": ["Bariadi District", "Bariadi Town", "Busega", "Itilima", "Maswa", "Meatu"],
    "Singida": ["Ikungi", "Iramba", "Manyoni", "Mkalama", "Singida District", "Singida Municipal"],
    "Songwe": ["Ileje", "Mbozi", "Momba", "Songwe", "Tunduma Town"],
    "Tabora": ["Igunga", "Kaliua", "Nzega District", "Nzega Town", "Sikonge", "Tabora Municipal", "Urambo", "Uyui"],
    "Tanga": ["Handeni District", "Handeni Town", "Kilindi", "Korogwe District", "Korogwe Town", "Lushoto", "Muheza", "Mkinga", "Pangani", "Tanga City"],
    "Kaskazini Unguja": ["Kaskazini A", "Kaskazini B"],
    "Kusini Unguja": ["Kati", "Kusini"],
    "Mjini Magharibi": ["Magharibi A", "Magharibi B", "Mjini"],
    "Kaskazini Pemba": ["Micheweni", "Wete"],
    "Kusini Pemba": ["Chake Chake", "Mkoani"],
}


def require_tanzania_region(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if cleaned not in TANZANIA_REGIONS:
        raise ValueError("location must be a Tanzania region")
    return cleaned


def require_district_in_region(region: str | None, district: str | None) -> str | None:
    if district is None:
        return None
    cleaned = str(district).strip()
    if not region:
        raise ValueError("region is required before selecting a district")
    allowed = DISTRICTS_BY_REGION.get(str(region).strip(), [])
    if cleaned not in allowed:
        raise ValueError("district must belong to the selected Tanzania region")
    return cleaned
