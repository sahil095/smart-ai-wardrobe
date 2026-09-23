"""Shared option lists derived from the PRD.

Kept in one place so both API validation and the UI (via /api/meta/options)
stay in sync.
"""

BODY_TYPES = ["Slim", "Athletic", "Average", "Muscular", "Heavy"]

SKIN_TONES = [
    "Fair",
    "Light",
    "Light Brown",
    "Medium Brown",
    "Olive",
    "Dark Brown",
    "Deep",
]

UNDERTONES = ["Cool", "Neutral", "Warm"]

HAIR_COLORS = ["Black", "Dark Brown", "Brown", "Light Brown", "Blonde", "Red", "Grey", "White", "Other"]

EYE_COLORS = ["Black", "Brown", "Hazel", "Green", "Blue", "Grey", "Other"]

GENDERS = ["Male", "Female", "Non-binary", "Prefer not to say"]

PREFERRED_FITS = ["Slim", "Regular", "Relaxed", "Oversized"]

FASHION_STYLES = [
    "Casual",
    "Streetwear",
    "Minimalist",
    "Business Casual",
    "Formal",
    "Smart Casual",
    "Athleisure",
    "Vintage",
    "Luxury",
]

CATEGORIES = [
    "Upper",
    "Lower",
    "Shoes",
    "Accessories",
    "Outerwear",
    "Activewear",
    "Sleepwear",
    "Ethnic",
]

SUBCATEGORIES = {
    "Upper": [
        "T-Shirt", "Polo", "Henley", "Shirt", "Overshirt", "Sweater",
        "Pullover", "Hoodie", "Crewneck", "Tank Top", "Kurta", "Blazer",
        "Vest", "Jersey",
    ],
    "Lower": [
        "Jeans", "Chinos", "Trousers", "Joggers", "Sweatpants", "Cargo Pants",
        "Shorts", "Formal Pants", "Track Pants", "Linen Pants",
    ],
    "Shoes": [
        "Sneakers", "Running Shoes", "Boots", "Loafers", "Sandals", "Slides",
        "Formal Shoes", "Chelsea Boots", "High Tops", "Canvas Shoes",
    ],
    "Outerwear": [
        "Denim Jacket", "Bomber", "Leather Jacket", "Winter Jacket",
        "Rain Jacket", "Coat", "Windbreaker", "Fleece", "Puffer",
    ],
    "Accessories": [
        "Watch", "Bracelet", "Chain", "Ring", "Cap", "Beanie", "Belt", "Tie",
        "Scarf", "Backpack", "Sunglasses", "Wallet",
    ],
    "Activewear": ["Jersey", "Track Pants", "Shorts", "Compression", "Other"],
    "Sleepwear": ["Pajama Top", "Pajama Bottom", "Nightwear", "Other"],
    "Ethnic": ["Kurta", "Sherwani", "Nehru Jacket", "Dhoti", "Other"],
}

PATTERNS = [
    "Plain", "Striped", "Printed", "Graphic", "Checked", "Plaid", "Floral",
    "Textured",
]

MATERIALS = [
    "Cotton", "Polyester", "Denim", "Leather", "Linen", "Wool", "Blended",
]

SEASONS = ["Spring", "Summer", "Fall", "Winter", "All Season"]

WEATHER_SUITABILITY = ["Hot", "Cold", "Rain", "Windy", "Snow"]

OCCASIONS = [
    "Casual", "Office", "Date", "Gym", "Party", "Wedding", "Travel",
    "Vacation", "Interview", "Formal", "Semi Formal", "College", "Home",
]

LAUNDRY_STATUSES = ["Clean", "Laundry", "Dry Cleaning", "Unavailable"]

WEAR_FREQUENCIES = ["Rarely", "Sometimes", "Often", "Daily"]

CONDITIONS = ["New", "Good", "Worn", "Old"]

SLEEVE_TYPES = ["Full Sleeve", "Half Sleeve", "Sleeveless", "3/4 Sleeve", "N/A"]

NECK_TYPES = ["Round", "V-Neck", "Collar", "Polo", "Turtleneck", "Henley", "N/A"]

TIME_OF_DAY = ["Morning", "Afternoon", "Evening", "Night"]

DRESS_CODES = ["Casual", "Smart Casual", "Business Casual", "Formal", "Black Tie"]

COMFORT_STYLE = ["Comfort", "Balanced", "Style"]

# Only these laundry statuses are eligible for AI recommendations.
CLEAN_STATUS = "Clean"

# ---- Phase 1: category-dependent fields & attributes ----

# Which existing base metadata fields are relevant per category. A field is
# shown when no category is selected yet, or the category is in its list.
CATEGORY_FIELD_VISIBILITY = {
    "sleeve_type": ["Upper", "Outerwear", "Ethnic", "Activewear", "Sleepwear"],
    "neck_type": ["Upper", "Ethnic", "Activewear", "Sleepwear"],
}

# Builtin fallback attribute schemas per category (used when the LLM is
# unavailable or returns nothing). Field type is 'select' (with options) or
# 'text'. These are intentionally short and practical for filtering.
BUILTIN_ATTRIBUTE_SCHEMAS = {
    "Upper": [
        {"key": "closure", "label": "Closure", "type": "select",
         "options": ["Pullover", "Button", "Zip", "Half-Zip"]},
        {"key": "hooded", "label": "Hooded", "type": "select",
         "options": ["Yes", "No"]},
    ],
    "Lower": [
        {"key": "rise", "label": "Rise", "type": "select",
         "options": ["Low", "Mid", "High"]},
        {"key": "leg_style", "label": "Leg Style", "type": "select",
         "options": ["Skinny", "Slim", "Straight", "Tapered", "Wide"]},
        {"key": "length", "label": "Length", "type": "select",
         "options": ["Full", "Cropped", "Shorts"]},
    ],
    "Shoes": [
        {"key": "closure", "label": "Closure", "type": "select",
         "options": ["Laces", "Slip-on", "Velcro", "Buckle", "Zip"]},
        {"key": "sole_type", "label": "Sole", "type": "select",
         "options": ["Rubber", "EVA", "Leather", "Gum"]},
        {"key": "shoe_height", "label": "Height", "type": "select",
         "options": ["Low-top", "Mid-top", "High-top"]},
    ],
    "Outerwear": [
        {"key": "closure", "label": "Closure", "type": "select",
         "options": ["Zip", "Button", "Open"]},
        {"key": "hooded", "label": "Hooded", "type": "select",
         "options": ["Yes", "No"]},
        {"key": "insulation", "label": "Insulation", "type": "select",
         "options": ["None", "Light", "Heavy"]},
        {"key": "water_resistant", "label": "Water Resistant", "type": "select",
         "options": ["Yes", "No"]},
    ],
    "Accessories": [
        {"key": "metal_tone", "label": "Metal Tone", "type": "select",
         "options": ["Gold", "Silver", "Rose Gold", "Black", "None"]},
        {"key": "adjustable", "label": "Adjustable", "type": "select",
         "options": ["Yes", "No"]},
    ],
    "Activewear": [
        {"key": "fit_type", "label": "Fit Type", "type": "select",
         "options": ["Compression", "Regular", "Loose"]},
        {"key": "moisture_wicking", "label": "Moisture Wicking", "type": "select",
         "options": ["Yes", "No"]},
    ],
    "Sleepwear": [
        {"key": "piece", "label": "Piece", "type": "select",
         "options": ["Top", "Bottom", "Set"]},
    ],
    "Ethnic": [
        {"key": "work_type", "label": "Work / Detailing", "type": "select",
         "options": ["Plain", "Embroidered", "Printed", "Embellished"]},
    ],
}


def all_options() -> dict:
    """Return every option list as a single JSON-serialisable dict for the UI."""
    return {
        "genders": GENDERS,
        "body_types": BODY_TYPES,
        "skin_tones": SKIN_TONES,
        "undertones": UNDERTONES,
        "hair_colors": HAIR_COLORS,
        "eye_colors": EYE_COLORS,
        "preferred_fits": PREFERRED_FITS,
        "fashion_styles": FASHION_STYLES,
        "categories": CATEGORIES,
        "subcategories": SUBCATEGORIES,
        "patterns": PATTERNS,
        "materials": MATERIALS,
        "seasons": SEASONS,
        "weather_suitability": WEATHER_SUITABILITY,
        "occasions": OCCASIONS,
        "laundry_statuses": LAUNDRY_STATUSES,
        "wear_frequencies": WEAR_FREQUENCIES,
        "conditions": CONDITIONS,
        "sleeve_types": SLEEVE_TYPES,
        "neck_types": NECK_TYPES,
        "time_of_day": TIME_OF_DAY,
        "dress_codes": DRESS_CODES,
        "comfort_style": COMFORT_STYLE,
        "category_field_visibility": CATEGORY_FIELD_VISIBILITY,
    }
