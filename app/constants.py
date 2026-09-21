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
    }
