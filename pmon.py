#!/usr/bin/env python3
'''Amazon price monitor script using Playwright.'''
import asyncio
import json
import sqlite3
import os
import logging
from datetime import datetime
from playwright.async_api import async_playwright as async_pw
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from product import Product

# Configuration variables
CONFIG = {
    "PRODUCTS_FILE_PATH": "products.json",
    "SCREENSHOTS_DIR": "screenshots",
    "HEADLESS_MODE": True,
    "TIMEOUT": 10000
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pmon.log'),
        logging.StreamHandler()
    ]
)


async def generate_ss_name(item):
    '''Generate a screenshot name based on the item name.'''
    include_ts = False  # False to keep only the latest screenshot
    timestamp = datetime.now().strftime('%Y%m%d_%H%M') if include_ts else ''
    item_name = item.replace(' ', '_').replace('/', '_')
    return f"{item_name}{'_' + timestamp if timestamp else ''}.png"


async def start(item, url, size):
    '''Start the Playwright browser and navigate to the given URL.'''
    try:
        async with async_pw() as pw:
            browser = await pw.chromium.launch(headless=CONFIG["HEADLESS_MODE"])
            page = await browser.new_page()
            await page.goto(url, timeout=CONFIG["TIMEOUT"])
            await page.wait_for_load_state('domcontentloaded')

            if size != '':
                await page.click(
                    f'''//span[contains(@class, 'swatch-title-text') and contains(text(), '{size}')]
                    /ancestor::span[@class='a-button-inner']/input''')
                await page.wait_for_load_state('domcontentloaded')

            try:
                price_lbl = page.locator(
                    "(//div[@id='corePrice_feature_div']//span[@class='a-offscreen'])[1]")
                await price_lbl.wait_for()
                price = await price_lbl.inner_text()
                logging.info("Current Price for %s is %s", item, price)
            except PlaywrightTimeoutError:
                logging.error("Price not found for %s", item)
                price = "N/A"

            ss_name = await generate_ss_name(item)
            ss_full_path = os.path.join(CONFIG["SCREENSHOTS_DIR"], ss_name)
            await page.screenshot(path=ss_full_path)
            return Product(item, price, url)
    except Exception as e:
        logging.error("Error processing %s: %s", item, str(e))
    finally:
        await browser.close()
        await pw.stop()


def product_url_iterator(file_path):
    '''Yield product URLs from a JSON file.'''
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            products = json.load(file)
            for prod in products:
                yield prod.get('item'), prod.get('url'), prod.get('size')
    except FileNotFoundError:
        logging.error("File not found: %s", file_path)
        raise
    except Exception as e:
        logging.error("Error reading file %s: %s", file_path, str(e))
        raise


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    url_iterator = product_url_iterator(CONFIG["PRODUCTS_FILE_PATH"])
    con = sqlite3.connect('data.db')
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

    for ITEM_NAME, ITEM_URL, ITEM_SIZE in url_iterator:
        product = asyncio.run(start(ITEM_NAME, ITEM_URL, ITEM_SIZE))
        if product:
            cursor.execute('''
                INSERT INTO price_history (item, price, url)
                VALUES (?, ?, ?)
            ''', (product.name, product.price, product.url))
            con.commit()
            logging.info("Inserted %s into database.", product.name)
    con.close()

    print("Script completed.")
