from recipe_scrapers import scrape_me

#url = "https://www.budgetbytes.com/creamy-garlic-chicken/"
#scraper = scrape_me(url)

#print("Title:", scraper.title())
#print("Ingredients:", scraper.ingredients())
#print("Instructions:", scraper.instructions())

def main():
    print("Hello! Welcome to Cooking Captain!")
    recipe_url = input("Please give me the link to your recipe: ").strip()

    scraper = scrape_me(recipe_url)
    print("Title: ", scraper.title())
    print("\nIngredients")
    for ingredient in scraper.ingredients():
        print("-", ingredient)
    print("\nInstructions:")
    print(scraper.instructions())
    print(scraper.to_json())
main()

