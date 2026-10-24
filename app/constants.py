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

# Columns filled from the dynamic filters so outfit generation still sees them.
PROMOTED_ATTRIBUTE_COLUMNS = {
    "pattern": "pattern",
    "material": "material",
    "fit": "fit",
    "sleeve_length": "sleeve_type",
    "neck_type": "neck_type",
}

# Short, plain explanations shown beside each dynamic filter.
FIELD_META = {
    "pattern": ("Pattern", "The look of the cloth, like plain, stripes, or a picture."),
    "material": ("Material", "What it is made from, like cotton or denim."),
    "fit": ("Fit", "How tight or loose it feels on your body."),
    "sleeve_length": ("Sleeve Length", "How far the sleeves go down your arm."),
    "neck_type": ("Neck Type", "The shape around the neck, like a collar or a v-neck."),
    "closure": ("Closure", "How it opens and closes, like buttons or a zip."),
    "hooded": ("Hooded", "Whether it has a hood you can pull up."),
    "rise": ("Rise", "How high the waist sits on your body."),
    "leg_style": ("Leg Style", "The shape of the leg, like straight or wide."),
    "length": ("Length", "How long it is from the waist to the hem."),
    "sole_type": ("Sole", "What the bottom of the shoe is made of."),
    "shoe_height": ("Height", "How high the shoe comes up on your ankle."),
    "insulation": ("Insulation", "How warm the inside filling is."),
    "water_resistant": ("Water Resistant", "Whether light rain stays off it."),
    "metal_tone": ("Metal Tone", "The metal color, like gold or silver."),
    "adjustable": ("Adjustable", "Whether you can change it to fit you."),
    "moisture_wicking": ("Moisture Wicking", "Whether it pulls sweat off your skin."),
    "work_type": ("Detailing", "Extra decoration, like stitching or beads."),
}


def _opt(key: str, options: list[str], label: str | None = None, help_text: str | None = None) -> dict:
    meta_label, meta_help = FIELD_META[key]
    return {
        "key": key,
        "label": label or meta_label,
        "type": "select",
        "options": list(options),
        "help": help_text or meta_help,
    }


def _patch(
    base: list[dict],
    drop: tuple[str, ...] = (),
    options: dict | None = None,
    help_text: dict | None = None,
    label: dict | None = None,
    extra: tuple = (),
) -> list[dict]:
    """Copy a category schema, then swap options or drop fields for one subcategory."""
    options = options or {}
    help_text = help_text or {}
    label = label or {}
    dropped = set(drop)
    out = []
    for field in base:
        key = field["key"]
        if key in dropped:
            continue
        out.append(_opt(
            key,
            options.get(key, field["options"]),
            label=label.get(key),
            help_text=help_text.get(key),
        ))
    front = []
    back = []
    for key, opts, lab, hlp in extra:
        field = _opt(key, opts, label=lab, help_text=hlp)
        if key == "pattern":
            front.append(field)
        else:
            back.append(field)
    return front + out + back


def _clone_fields(fields: list[dict]) -> list[dict]:
    cloned = []
    for field in fields:
        copy = {
            "key": field["key"],
            "label": field["label"],
            "type": field["type"],
            "help": field["help"],
        }
        if field.get("options") is not None:
            copy["options"] = list(field["options"])
        cloned.append(copy)
    return cloned


# Category defaults. A subcategory schema below replaces this once one is chosen.
CATEGORY_SCHEMAS = {
    "Upper": [
        _opt("pattern", ["Plain", "Striped", "Printed", "Graphic", "Checked", "Plaid", "Floral", "Textured"]),
        _opt("material", ["Cotton", "Polyester", "Linen", "Wool", "Fleece", "Blended"]),
        _opt("fit", ["Slim", "Regular", "Relaxed", "Oversized"]),
        _opt("sleeve_length", ["Full Sleeve", "Half Sleeve", "Sleeveless", "3/4 Sleeve"]),
        _opt("neck_type", ["Round", "V-Neck", "Collar", "Polo", "Turtleneck", "Henley", "Crew", "Scoop"]),
        _opt("closure", ["Pullover", "Button", "Zip", "Half-Zip"]),
        _opt("hooded", ["Yes", "No"]),
    ],
    "Lower": [
        _opt("pattern", ["Plain", "Striped", "Checked", "Plaid", "Printed", "Textured"]),
        _opt("material", ["Denim", "Cotton", "Polyester", "Linen", "Wool", "Blended"]),
        _opt("fit", ["Skinny", "Slim", "Regular", "Relaxed", "Oversized"]),
        _opt("rise", ["Low", "Mid", "High"]),
        _opt("leg_style", ["Skinny", "Slim", "Straight", "Tapered", "Wide"]),
        _opt("length", ["Full", "Cropped", "Shorts"]),
    ],
    "Shoes": [
        _opt("pattern", ["Plain", "Color-block", "Printed", "Textured"]),
        _opt("material", ["Leather", "Canvas", "Mesh", "Suede", "Synthetic", "Rubber"]),
        _opt("closure", ["Laces", "Slip-on", "Velcro", "Buckle", "Zip"]),
        _opt("sole_type", ["Rubber", "EVA", "Leather", "Gum"]),
        _opt("shoe_height", ["Low-top", "Mid-top", "High-top"]),
    ],
    "Outerwear": [
        _opt("pattern", ["Plain", "Checked", "Plaid", "Quilted", "Color-block", "Printed"]),
        _opt("material", ["Denim", "Leather", "Wool", "Polyester", "Nylon", "Cotton", "Fleece", "Down"]),
        _opt("fit", ["Slim", "Regular", "Relaxed", "Oversized"]),
        _opt("sleeve_length", ["Full Sleeve", "3/4 Sleeve"]),
        _opt("neck_type", ["Collar", "Hood", "Lapel", "Stand", "Crew"]),
        _opt("closure", ["Zip", "Button", "Open"]),
        _opt("hooded", ["Yes", "No"]),
        _opt("insulation", ["None", "Light", "Heavy"]),
        _opt("water_resistant", ["Yes", "No"]),
    ],
    "Accessories": [
        _opt("material", ["Metal", "Leather", "Cotton", "Fabric", "Plastic"]),
        _opt("metal_tone", ["Gold", "Silver", "Rose Gold", "Black", "None"]),
        _opt("adjustable", ["Yes", "No"]),
    ],
    "Activewear": [
        _opt("pattern", ["Plain", "Striped", "Printed", "Color-block"]),
        _opt("material", ["Polyester", "Nylon", "Cotton", "Spandex", "Mesh", "Blended"]),
        _opt("fit", ["Compression", "Regular", "Loose"]),
        _opt("sleeve_length", ["Half Sleeve", "Sleeveless", "Full Sleeve"]),
        _opt("neck_type", ["Round", "V-Neck", "Collar"]),
        _opt("moisture_wicking", ["Yes", "No"]),
    ],
    "Ethnic": [
        _opt("pattern", ["Plain", "Printed", "Embroidered", "Striped"]),
        _opt("material", ["Cotton", "Silk", "Linen", "Wool", "Blended"]),
        _opt("fit", ["Slim", "Regular", "Relaxed"]),
        _opt("sleeve_length", ["Full Sleeve", "Half Sleeve", "3/4 Sleeve"]),
        _opt("neck_type", ["Mandarin", "Collar", "Round", "V-Neck"]),
        _opt("work_type", ["Plain", "Embroidered", "Printed", "Embellished"]),
    ],
}

# Option and drop overrides. Missing subcategories use the category default.
_SUB_SPEC: dict[tuple[str, str], dict] = {
    ("Upper", "T-Shirt"): {"drop": ("hooded", "closure"), "options": {
        "pattern": ["Plain", "Striped", "Graphic", "Printed", "Textured"],
        "material": ["Cotton", "Polyester", "Linen", "Blended"],
        "sleeve_length": ["Half Sleeve", "Sleeveless", "Full Sleeve"],
        "neck_type": ["Round", "V-Neck", "Crew", "Scoop"],
    }},
    ("Upper", "Polo"): {"drop": ("hooded",), "options": {
        "pattern": ["Plain", "Striped", "Printed"],
        "material": ["Cotton", "Pique", "Polyester", "Blended"],
        "sleeve_length": ["Half Sleeve", "Full Sleeve"],
        "neck_type": ["Polo", "Collar"],
        "closure": ["Button", "Pullover"],
    }},
    ("Upper", "Henley"): {"drop": ("hooded",), "options": {
        "pattern": ["Plain", "Striped", "Textured"],
        "material": ["Cotton", "Polyester", "Blended"],
        "sleeve_length": ["Half Sleeve", "Full Sleeve", "3/4 Sleeve"],
        "neck_type": ["Henley", "Grandad", "Round"],
        "closure": ["Pullover", "Button"],
    }},
    ("Upper", "Shirt"): {"drop": ("hooded",), "options": {
        "pattern": ["Plain", "Striped", "Checked", "Printed"],
        "material": ["Cotton", "Linen", "Polyester", "Oxford", "Blended"],
        "sleeve_length": ["Full Sleeve", "Half Sleeve", "3/4 Sleeve"],
        "neck_type": ["Collar", "Button-down", "Spread", "Band"],
        "closure": ["Button", "Snap"],
    }},
    ("Upper", "Overshirt"): {"options": {
        "pattern": ["Plain", "Checked", "Plaid", "Striped"],
        "material": ["Cotton", "Flannel", "Denim", "Wool", "Linen"],
        "sleeve_length": ["Full Sleeve", "Half Sleeve"],
        "neck_type": ["Collar", "Camp", "Band"],
        "closure": ["Button", "Zip", "Open"],
    }},
    ("Upper", "Sweater"): {"options": {
        "pattern": ["Plain", "Cable", "Ribbed", "Striped", "Fair Isle"],
        "material": ["Wool", "Cotton", "Cashmere", "Acrylic", "Blended"],
        "sleeve_length": ["Full Sleeve", "3/4 Sleeve"],
        "neck_type": ["Round", "V-Neck", "Turtleneck", "Crew", "Mock Neck"],
        "closure": ["Pullover", "Button", "Zip", "Half-Zip"],
    }},
    ("Upper", "Pullover"): {"drop": ("closure",), "options": {
        "pattern": ["Plain", "Striped", "Color-block", "Textured"],
        "material": ["Wool", "Cotton", "Fleece", "Acrylic", "Blended"],
        "sleeve_length": ["Full Sleeve", "3/4 Sleeve"],
        "neck_type": ["Round", "V-Neck", "Crew", "Turtleneck", "Mock Neck"],
    }},
    ("Upper", "Hoodie"): {"drop": ("sleeve_length",), "options": {
        "pattern": ["Plain", "Graphic", "Color-block", "Printed"],
        "material": ["Cotton", "Fleece", "Polyester", "Blended"],
        "neck_type": ["Hood", "Crew"],
        "closure": ["Pullover", "Zip", "Half-Zip"],
    }},
    ("Upper", "Crewneck"): {"drop": ("hooded", "closure", "sleeve_length"), "options": {
        "pattern": ["Plain", "Graphic", "Striped"],
        "material": ["Cotton", "Fleece", "Wool", "Blended"],
        "neck_type": ["Crew", "Round"],
    }},
    ("Upper", "Tank Top"): {"drop": ("sleeve_length", "hooded", "closure"), "options": {
        "pattern": ["Plain", "Graphic", "Striped", "Printed"],
        "material": ["Cotton", "Polyester", "Mesh", "Blended"],
        "neck_type": ["Round", "Scoop", "V-Neck", "Racerback"],
    }},
    ("Upper", "Kurta"): {"drop": ("hooded",), "options": {
        "pattern": ["Plain", "Printed", "Embroidered", "Striped"],
        "material": ["Cotton", "Linen", "Silk", "Blended"],
        "sleeve_length": ["Full Sleeve", "Half Sleeve", "3/4 Sleeve"],
        "neck_type": ["Mandarin", "Collar", "Round", "V-Neck"],
        "closure": ["Button", "Pullover"],
    }},
    ("Upper", "Blazer"): {"drop": ("hooded", "sleeve_length"), "options": {
        "pattern": ["Plain", "Checked", "Pinstripe", "Textured"],
        "material": ["Wool", "Cotton", "Linen", "Polyester", "Blended"],
        "fit": ["Slim", "Regular", "Relaxed"],
        "neck_type": ["Lapel", "Shawl", "Collar"],
        "closure": ["Button", "Open", "Double-breasted"],
    }},
    ("Upper", "Vest"): {"drop": ("sleeve_length", "hooded"), "options": {
        "pattern": ["Plain", "Quilted", "Checked"],
        "material": ["Wool", "Cotton", "Fleece", "Denim", "Polyester"],
        "neck_type": ["Round", "V-Neck", "Collar"],
        "closure": ["Button", "Zip", "Open"],
    }},
    ("Upper", "Jersey"): {"drop": ("hooded", "closure"), "options": {
        "pattern": ["Plain", "Striped", "Printed", "Color-block"],
        "material": ["Polyester", "Mesh", "Cotton", "Blended"],
        "sleeve_length": ["Half Sleeve", "Sleeveless", "Full Sleeve"],
        "neck_type": ["Round", "V-Neck", "Collar"],
    }},
    ("Lower", "Jeans"): {"options": {
        "pattern": ["Plain", "Distressed", "Faded", "Striped"],
        "material": ["Denim", "Stretch Denim"],
        "fit": ["Skinny", "Slim", "Straight", "Relaxed", "Wide"],
        "length": ["Full", "Cropped"],
    }},
    ("Lower", "Chinos"): {"options": {
        "pattern": ["Plain", "Textured"],
        "material": ["Cotton", "Stretch Cotton"],
        "fit": ["Slim", "Regular", "Relaxed"],
        "leg_style": ["Slim", "Straight", "Tapered"],
        "length": ["Full", "Cropped"],
    }},
    ("Lower", "Trousers"): {"options": {
        "pattern": ["Plain", "Pinstripe", "Checked"],
        "material": ["Wool", "Cotton", "Polyester", "Linen", "Blended"],
        "fit": ["Slim", "Regular", "Relaxed"],
        "leg_style": ["Slim", "Straight", "Wide", "Tapered"],
    }},
    ("Lower", "Joggers"): {"options": {
        "pattern": ["Plain", "Color-block", "Printed"],
        "material": ["Cotton", "Fleece", "Polyester"],
        "fit": ["Slim", "Relaxed"],
        "leg_style": ["Slim", "Tapered", "Straight"],
        "length": ["Full", "Cropped"],
    }},
    ("Lower", "Sweatpants"): {"options": {
        "pattern": ["Plain", "Color-block"],
        "material": ["Fleece", "Cotton", "Polyester"],
        "fit": ["Relaxed", "Regular"],
        "leg_style": ["Straight", "Tapered", "Wide"],
    }},
    ("Lower", "Cargo Pants"): {"options": {
        "pattern": ["Plain", "Camo"],
        "material": ["Cotton", "Canvas", "Nylon"],
        "fit": ["Relaxed", "Regular"],
        "leg_style": ["Straight", "Wide"],
        "length": ["Full", "Cropped"],
    }},
    ("Lower", "Shorts"): {"options": {
        "pattern": ["Plain", "Striped", "Printed", "Checked"],
        "material": ["Cotton", "Denim", "Linen", "Polyester"],
        "fit": ["Slim", "Regular", "Relaxed"],
        "length": ["Short", "Mid", "Long"],
    }, "help_text": {"length": "How long the shorts are."}},
    ("Lower", "Formal Pants"): {"drop": ("length",), "options": {
        "pattern": ["Plain", "Pinstripe"],
        "material": ["Wool", "Polyester", "Blended"],
        "fit": ["Slim", "Regular"],
        "leg_style": ["Slim", "Straight"],
    }},
    ("Lower", "Track Pants"): {"options": {
        "pattern": ["Plain", "Striped", "Color-block"],
        "material": ["Polyester", "Nylon"],
        "fit": ["Slim", "Regular", "Relaxed"],
        "leg_style": ["Slim", "Straight", "Tapered"],
        "length": ["Full", "Cropped"],
    }},
    ("Lower", "Linen Pants"): {"options": {
        "pattern": ["Plain", "Striped"],
        "material": ["Linen", "Linen Blend"],
        "fit": ["Relaxed", "Regular", "Wide"],
        "leg_style": ["Straight", "Wide"],
        "length": ["Full", "Cropped"],
    }},
    ("Shoes", "Sneakers"): {"options": {
        "pattern": ["Plain", "Color-block", "Printed", "Textured"],
        "material": ["Leather", "Canvas", "Mesh", "Suede", "Synthetic"],
        "closure": ["Laces", "Slip-on", "Velcro"],
        "sole_type": ["Rubber", "EVA", "Gum"],
    }},
    ("Shoes", "Running Shoes"): {"drop": ("shoe_height",), "options": {
        "pattern": ["Plain", "Color-block", "Reflective"],
        "material": ["Mesh", "Synthetic", "Knit"],
        "closure": ["Laces", "Slip-on"],
        "sole_type": ["Rubber", "EVA"],
    }},
    ("Shoes", "Boots"): {"options": {
        "pattern": ["Plain", "Textured"],
        "material": ["Leather", "Suede", "Rubber"],
        "closure": ["Laces", "Zip", "Slip-on"],
        "sole_type": ["Rubber", "Leather"],
        "shoe_height": ["Ankle", "Mid-calf", "Knee"],
    }},
    ("Shoes", "Loafers"): {"drop": ("shoe_height",), "options": {
        "pattern": ["Plain", "Textured"],
        "material": ["Leather", "Suede"],
        "closure": ["Slip-on", "Buckle"],
        "sole_type": ["Leather", "Rubber"],
    }},
    ("Shoes", "Sandals"): {"drop": ("shoe_height",), "options": {
        "pattern": ["Plain", "Printed"],
        "material": ["Leather", "Rubber", "Synthetic"],
        "closure": ["Slip-on", "Buckle", "Strap"],
        "sole_type": ["Rubber", "Leather"],
    }},
    ("Shoes", "Slides"): {"drop": ("shoe_height", "closure"), "options": {
        "pattern": ["Plain", "Printed"],
        "material": ["Rubber", "Foam", "Leather"],
        "sole_type": ["Rubber", "Foam"],
    }},
    ("Shoes", "Formal Shoes"): {"drop": ("shoe_height", "material"), "options": {
        "pattern": ["Plain", "Textured"],
        "closure": ["Laces", "Slip-on", "Buckle"],
        "sole_type": ["Leather", "Rubber"],
    }},
    ("Shoes", "Chelsea Boots"): {"drop": ("shoe_height", "closure"), "options": {
        "pattern": ["Plain", "Textured"],
        "material": ["Leather", "Suede"],
        "sole_type": ["Rubber", "Leather"],
    }},
    ("Shoes", "High Tops"): {"drop": ("shoe_height", "closure"), "options": {
        "pattern": ["Plain", "Color-block", "Printed"],
        "material": ["Canvas", "Leather", "Synthetic"],
        "sole_type": ["Rubber", "Gum"],
    }},
    ("Shoes", "Canvas Shoes"): {"drop": ("material",), "options": {
        "pattern": ["Plain", "Printed", "Striped"],
        "closure": ["Laces", "Slip-on"],
        "sole_type": ["Rubber", "Gum"],
        "shoe_height": ["Low-top", "High-top"],
    }},
    ("Outerwear", "Denim Jacket"): {"drop": ("sleeve_length", "insulation", "material"), "options": {
        "pattern": ["Plain", "Distressed", "Faded"],
        "neck_type": ["Collar", "Band"],
        "closure": ["Button", "Zip"],
    }},
    ("Outerwear", "Bomber"): {"drop": ("sleeve_length", "closure"), "options": {
        "pattern": ["Plain", "Color-block"],
        "material": ["Nylon", "Leather", "Polyester"],
        "neck_type": ["Ribbed", "Collar"],
        "insulation": ["None", "Light"],
    }},
    ("Outerwear", "Leather Jacket"): {"drop": ("sleeve_length", "insulation", "material"), "options": {
        "pattern": ["Plain", "Quilted"],
        "neck_type": ["Collar", "Lapel"],
        "closure": ["Zip", "Button"],
    }},
    ("Outerwear", "Winter Jacket"): {"drop": ("sleeve_length",), "options": {
        "pattern": ["Plain", "Quilted", "Color-block"],
        "material": ["Polyester", "Down", "Wool"],
        "insulation": ["Heavy", "Light"],
        "neck_type": ["Hood", "Collar"],
        "closure": ["Zip", "Button"],
    }},
    ("Outerwear", "Rain Jacket"): {"drop": ("sleeve_length", "closure"), "options": {
        "pattern": ["Plain", "Color-block"],
        "material": ["Nylon", "Polyester"],
        "insulation": ["None", "Light"],
        "neck_type": ["Hood", "Collar"],
    }},
    ("Outerwear", "Coat"): {"drop": ("sleeve_length",), "options": {
        "pattern": ["Plain", "Checked", "Plaid"],
        "material": ["Wool", "Cashmere", "Polyester", "Cotton"],
        "neck_type": ["Lapel", "Collar"],
        "closure": ["Button", "Open"],
    }, "extra": (("length", ["Short", "Mid", "Long"], "Length", "How far down the coat hangs."),)},
    ("Outerwear", "Windbreaker"): {"drop": ("sleeve_length", "closure"), "options": {
        "pattern": ["Plain", "Color-block"],
        "material": ["Nylon", "Polyester"],
        "insulation": ["None", "Light"],
        "neck_type": ["Hood", "Collar"],
    }},
    ("Outerwear", "Fleece"): {"drop": ("sleeve_length", "material"), "options": {
        "pattern": ["Plain", "Color-block", "Printed"],
        "neck_type": ["Collar", "Crew", "Hood"],
        "closure": ["Zip", "Pullover", "Button"],
        "insulation": ["Light", "None"],
    }},
    ("Outerwear", "Puffer"): {"drop": ("sleeve_length", "closure"), "options": {
        "pattern": ["Plain", "Quilted", "Color-block"],
        "material": ["Nylon", "Polyester"],
        "insulation": ["Heavy", "Light"],
        "neck_type": ["Hood", "Collar"],
    }},
    ("Accessories", "Watch"): {"options": {
        "material": ["Metal", "Leather", "Rubber", "Fabric", "Ceramic"],
    }},
    ("Accessories", "Bracelet"): {"options": {
        "material": ["Metal", "Leather", "Beads", "Fabric"],
    }},
    ("Accessories", "Chain"): {"drop": ("material",)},
    ("Accessories", "Ring"): {"drop": ("material",)},
    ("Accessories", "Cap"): {"drop": ("metal_tone",), "options": {
        "pattern": ["Plain", "Logo", "Striped"],
        "material": ["Cotton", "Wool", "Polyester"],
    }, "extra": (("pattern", ["Plain", "Logo", "Striped"], None, None),)},
    ("Accessories", "Beanie"): {"drop": ("metal_tone", "adjustable"), "extra": (
        ("pattern", ["Plain", "Ribbed", "Striped"], None, None),
    ), "options": {"material": ["Wool", "Acrylic", "Cotton"]}},
    ("Accessories", "Belt"): {"options": {
        "material": ["Leather", "Fabric", "Canvas"],
    }, "help_text": {"metal_tone": "The color of the buckle."}, "extra": (
        ("pattern", ["Plain", "Textured"], None, None),
    )},
    ("Accessories", "Tie"): {"drop": ("metal_tone", "adjustable"), "options": {
        "material": ["Silk", "Polyester", "Cotton"],
    }, "extra": (("pattern", ["Plain", "Striped", "Printed", "Paisley"], None, None),)},
    ("Accessories", "Scarf"): {"drop": ("metal_tone", "adjustable"), "options": {
        "material": ["Wool", "Cotton", "Silk", "Cashmere"],
    }, "extra": (("pattern", ["Plain", "Striped", "Checked", "Printed"], None, None),)},
    ("Accessories", "Backpack"): {"drop": ("metal_tone",), "options": {
        "material": ["Nylon", "Canvas", "Leather"],
    }, "extra": (("closure", ["Zip", "Drawstring", "Buckle"], None, None),)},
    ("Accessories", "Sunglasses"): {"options": {
        "material": ["Plastic", "Metal"],
    }},
    ("Accessories", "Wallet"): {"drop": ("metal_tone", "adjustable"), "options": {
        "material": ["Leather", "Fabric"],
    }},
    ("Activewear", "Jersey"): {"options": {
        "pattern": ["Plain", "Striped", "Printed", "Color-block"],
        "material": ["Polyester", "Mesh", "Cotton"],
    }},
    ("Activewear", "Track Pants"): {"drop": ("sleeve_length", "neck_type"), "options": {
        "pattern": ["Plain", "Striped", "Color-block"],
        "material": ["Polyester", "Nylon"],
        "fit": ["Slim", "Regular", "Loose"],
    }},
    ("Activewear", "Shorts"): {"drop": ("sleeve_length", "neck_type"), "options": {
        "pattern": ["Plain", "Printed", "Color-block"],
        "material": ["Polyester", "Cotton"],
        "fit": ["Regular", "Loose", "Compression"],
    }},
    ("Activewear", "Compression"): {"drop": ("pattern",), "options": {
        "material": ["Spandex", "Nylon", "Polyester"],
        "fit": ["Compression", "Regular"],
    }},
    ("Ethnic", "Kurta"): {"options": {
        "pattern": ["Plain", "Printed", "Embroidered", "Striped"],
        "material": ["Cotton", "Linen", "Silk", "Blended"],
        "sleeve_length": ["Full Sleeve", "Half Sleeve", "3/4 Sleeve"],
        "neck_type": ["Mandarin", "Collar", "Round", "V-Neck"],
    }},
    ("Ethnic", "Sherwani"): {"drop": ("sleeve_length",), "options": {
        "pattern": ["Plain", "Embroidered", "Embellished"],
        "material": ["Silk", "Wool", "Blended"],
        "fit": ["Slim", "Regular"],
        "neck_type": ["Mandarin", "Collar", "Shawl"],
        "work_type": ["Embroidered", "Embellished", "Plain"],
    }},
    ("Ethnic", "Nehru Jacket"): {"options": {
        "pattern": ["Plain", "Embroidered", "Textured"],
        "material": ["Wool", "Cotton", "Silk"],
        "sleeve_length": ["Full Sleeve", "Sleeveless"],
        "neck_type": ["Mandarin", "Collar"],
        "work_type": ["Plain", "Embroidered"],
    }, "extra": (("closure", ["Button", "Open"], None, None),)},
    ("Ethnic", "Dhoti"): {"drop": ("sleeve_length", "neck_type", "fit"), "options": {
        "pattern": ["Plain", "Striped", "Printed"],
        "material": ["Cotton", "Silk"],
        "work_type": ["Plain", "Embroidered"],
    }},
}


def _build_subcategory_schemas() -> dict[tuple[str, str], list[dict]]:
    built: dict[tuple[str, str], list[dict]] = {}
    for key, spec in _SUB_SPEC.items():
        category, _sub = key
        built[key] = _patch(CATEGORY_SCHEMAS[category], **spec)
    return built


SUBCATEGORY_SCHEMAS = _build_subcategory_schemas()


def attribute_schema(category: str, subcategory: str | None = None) -> list[dict]:
    """Curated filters for a category, narrowed further when a subcategory is set."""
    base = CATEGORY_SCHEMAS.get(category)
    if not base:
        return []
    sub = (subcategory or "").strip()
    chosen = SUBCATEGORY_SCHEMAS.get((category, sub), base)
    return _clone_fields(chosen)


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
