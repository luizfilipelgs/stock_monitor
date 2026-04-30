import sqlite3
from celery import Celery
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService


app = Celery(
    main='tasks',
    broker='pyamqp://guest@localhost//',
    backend='db+sqlite:///celery.sqlite',
)


@app.task
def get_stock_price(stock_name):
    driver = webdriver.Chrome(
        service=ChromeService
        (ChromeDriverManager().install())
    )

    url = 'https://www.google.com'

    driver.get(url)

    search_input = driver.find_element(
        By.XPATH,
        '//textarea[@aria-label="Pesquisar"]'
    )
    search_input.send_keys(f'preço da ação {stock_name}')
    search_input.send_keys(Keys.ENTER)

    sleep(2)

    price_div = driver.find_element(
        By.XPATH,
        '//div[@data-attrid="Price"]'
    )
    price = price_div.find_elements(
        By.TAG_NAME,
        'span'
    )[2].text.replace(',', '.')

    driver.quit()

    with sqlite3.connect('stocks.db') as conn:
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS STOCKS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_name TEXT,
            price REAL,
            moment DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        INSERT OR IGNORE INTO STOCKS (stock_name, price)
        VALUES (?, ?)
        ''', (stock_name, price))

        conn.commit()

    return price
