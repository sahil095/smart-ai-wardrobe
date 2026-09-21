"""Optional: seed a demo user + a few clean items so you can test the generator.

Run from the project root:  python -m scripts.seed_demo
"""
from app.database import SessionLocal, init_db
from app.models import User, WardrobeItem


def run():
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Users already exist — skipping seed.")
            return

        user = User(
            name="Demo User",
            nickname="Demo",
            age=27,
            gender="Male",
            body_type="Athletic",
            skin_tone="Light Brown",
            undertone="Warm",
            preferred_fit="Regular",
            style=["Casual", "Minimalist", "Smart Casual"],
            favorite_colors=["navy", "white", "olive"],
            disliked_colors=["neon"],
            default_shoe_size="UK 9",
        )
        db.add(user)
        db.flush()

        items = [
            dict(name="White Oxford Shirt", category="Upper", subcategory="Shirt",
                 primary_color="White", material="Cotton", fit="Regular",
                 occasion=["Office", "Casual", "Date"], weather=["Hot", "Mild"],
                 season=["All Season"]),
            dict(name="Navy Crewneck Tee", category="Upper", subcategory="Crewneck",
                 primary_color="Navy", material="Cotton", fit="Regular",
                 occasion=["Casual", "College", "Home"], weather=["Hot"],
                 season=["Summer", "Spring"]),
            dict(name="Grey Hoodie", category="Upper", subcategory="Hoodie",
                 primary_color="Grey", material="Cotton", fit="Relaxed",
                 occasion=["Casual", "College", "Gym"], weather=["Cold"],
                 season=["Fall", "Winter"]),
            dict(name="Dark Wash Jeans", category="Lower", subcategory="Jeans",
                 primary_color="Blue", material="Denim", fit="Slim",
                 occasion=["Casual", "Date", "College"], weather=["Cold", "Mild"],
                 season=["All Season"]),
            dict(name="Beige Chinos", category="Lower", subcategory="Chinos",
                 primary_color="Beige", material="Cotton", fit="Regular",
                 occasion=["Office", "Casual", "Date"], weather=["Hot", "Mild"],
                 season=["Spring", "Summer"]),
            dict(name="White Sneakers", category="Shoes", subcategory="Sneakers",
                 primary_color="White", material="Leather", fit="Regular",
                 occasion=["Casual", "College", "Date"], weather=["Hot", "Mild"],
                 season=["All Season"]),
            dict(name="Brown Chelsea Boots", category="Shoes", subcategory="Chelsea Boots",
                 primary_color="Brown", material="Leather",
                 occasion=["Office", "Date", "Semi Formal"], weather=["Cold"],
                 season=["Fall", "Winter"]),
            dict(name="Denim Jacket", category="Outerwear", subcategory="Denim Jacket",
                 primary_color="Blue", material="Denim",
                 occasion=["Casual", "College"], weather=["Cold", "Windy"],
                 season=["Spring", "Fall"]),
            dict(name="Silver Watch", category="Accessories", subcategory="Watch",
                 primary_color="Silver", occasion=["Office", "Date", "Casual"],
                 season=["All Season"]),
        ]
        for data in items:
            db.add(WardrobeItem(user_id=user.id, laundry_status="Clean",
                                wear_frequency="Often", favorite=False, **data))

        db.commit()
        print(f"Seeded demo user (id={user.id}) with {len(items)} clean items.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
