# test_db.py
from dao.products_dao import ProductDAO

def main():
    products = ProductDAO.search_by_keyword("牛乳")
    for p in products:
        print(p.id, p.jan, p.name, p.brand, p.category)

if __name__ == "__main__":
    main()
