'''represents a product with its name, price, and URL'''


class Product:
    '''Represents a product with its name, price, and URL.'''

    def __init__(self, name, price, url):
        self.name = name
        self.price = price
        self.url = url

    def __str__(self):
        return f"Product(name={self.name}, price={self.price})"
