"""Create a reproducible synthetic sales database.   python -m data.seed_db"""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, country TEXT, segment TEXT, signup_date TEXT);
CREATE TABLE products (product_id INTEGER PRIMARY KEY, name TEXT, category TEXT, unit_price REAL);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers, product_id INTEGER REFERENCES products,
                     quantity INTEGER, order_date TEXT, status TEXT);
"""
COUNTRIES = ["Egypt", "Germany", "USA", "UK", "UAE", "France", "Canada"]
SEGMENTS = ["Consumer", "SMB", "Enterprise"]
PRODUCTS = [("Laptop", "Electronics", 950), ("Phone", "Electronics", 620), ("Headphones", "Electronics", 120),
            ("Monitor", "Electronics", 280), ("Desk", "Furniture", 340), ("Chair", "Furniture", 210),
            ("Bookshelf", "Furniture", 150), ("Notebook", "Stationery", 4), ("Pen Set", "Stationery", 12),
            ("Planner", "Stationery", 18), ("Backpack", "Accessories", 65), ("Wallet", "Accessories", 40)]


def seed(path: Path, seed_value: int = 42) -> None:
    rng = random.Random(seed_value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?)",
        [(i, f"Customer {i:02d}", rng.choice(COUNTRIES), rng.choice(SEGMENTS),
          str(date(2024, 1, 1) + timedelta(days=rng.randint(0, 400)))) for i in range(1, 41)],
    )
    conn.executemany("INSERT INTO products VALUES (?,?,?,?)",
                     [(i, n, c, p) for i, (n, c, p) in enumerate(PRODUCTS, 1)])
    conn.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?,?)",
        [(i, rng.randint(1, 40), rng.randint(1, len(PRODUCTS)), rng.randint(1, 5),
          str(date(2025, 1, 1) + timedelta(days=rng.randint(0, 364))),
          rng.choices(["completed", "cancelled", "pending"], [0.8, 0.1, 0.1])[0]) for i in range(1, 601)],
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    out = Path(__file__).parent / "sales.db"
    seed(out)
    print(f"Created {out}")
