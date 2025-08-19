import sqlite3
from datetime import datetime
from product import Product


class PriceRepository:
    '''Repository class for managing database operations related to price monitoring.'''

    def __init__(self, db_path='data.db'):
        '''Initialize the repository with the database path.'''
        self.db_path = db_path
        self.initialize_db()

    def initialize_db(self):
        '''Initialize the database and create the necessary tables if they do not exist.'''
        with sqlite3.connect(self.db_path) as con:
            cursor = con.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT NOT NULL,
                    price TEXT NOT NULL,
                    url TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            con.commit()

    def save_price(self, product: Product):
        '''Insert a new product price into the database.'''
        try:
            with sqlite3.connect(self.db_path) as con:
                cursor = con.cursor()
                cursor.execute('''
                    INSERT INTO price_history (item, price, url)
                    VALUES (?, ?, ?)
                ''', (product.name, product.price, product.url))
                con.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error saving price to database: {e}")
        return None

    def get_last_price(self, item_name):
        '''Retrieve the last recorded price for a given item.'''
        try:
            with sqlite3.connect(self.db_path) as con:
                cursor = con.cursor()
                cursor.execute('''
                    SELECT price FROM price_history
                    WHERE item = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (item_name,))
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error retrieving last price: {e}")
        return None

    def get_report_data(self, data_points=12):
        '''Retrieve data in json format for the report source.'''
        try:
            with sqlite3.connect(self.db_path) as con:
                cursor = con.cursor()
                cursor.execute(f'''
                    SELECT item, price, timestamp, url
                    FROM (
                    SELECT
                        item,
                        price,
                        timestamp,
                        url,
                        ROW_NUMBER() OVER (PARTITION BY item ORDER BY timestamp DESC) AS rn
                    FROM price_history
                )
                WHERE rn <= {data_points};
                ''')
                data = cursor.fetchall()
                items_dict = {}
                for item, price, timestamp, url in data:
                    # print(f"Item: {item}, URL: {url}")
                    if item not in items_dict:
                        items_dict[item] = {
                            'item': item,
                            'url': url,
                            'price_history': {}
                        }
                        items_dict[item]['price_history'][timestamp] = price

            # Convert dictionary to list for JSON serialization
            return list(items_dict.values())
        except sqlite3.Error as e:
            print(f"Error retrieving report data: {e}")
        return []
