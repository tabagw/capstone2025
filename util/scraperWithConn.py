"""
Simple recipe scraper - only gets title, time, ingredients, and instructions
"""

import mysql.connector
from recipe_scrapers import scrape_me
from recipe_scrapers import SCRAPERS
SCRAPERS.keys()

class RecipeDatabasePopulator:
    def __init__(self, db_config):
        """
        Initialize with MySQL database configuration
        
        db_config = {
            'host': 'localhost',
            'user': 'your_username',
            'password': 'your_password',
            'database': 'recipe_db'
        }
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        self.conn = mysql.connector.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        print("✓ Connected to database")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✓ Database connection closed")

    def recipe_exists(self, url): 
        """Check to see if recipe URL already exists"""
        self.cursor.execute(
            "SELECT recipe_id FROM recipes WHERE source_url = %s", (url,)
        )
        return self.cursor.fetchone() is not None
    
    def get_or_create_ingredient(self, ingredient_name):
        """Get ingredient_id or create new ingredient"""
        ingredient_name = ingredient_name.lower().strip()
        
        self.cursor.execute(
            "SELECT ingredient_id FROM ingredients WHERE name = %s",
            (ingredient_name,)
        )
        result = self.cursor.fetchone()
        
        if result:
            return result[0]
        
        self.cursor.execute(
            "INSERT INTO ingredients (name, category) VALUES (%s, %s)",
            (ingredient_name, 'other')
        )
        return self.cursor.lastrowid
    
    def scrape_and_insert_recipe(self, url):
        """Scrape recipe from URL and insert into database"""
        try:
            if self.recipe_exists(url):
                print(f" Recipe already exists")
                return False
            # Scrape the recipe
            scraper = scrape_me(url, wild_mode = True)
            
            # Get the data
            title = scraper.title()
            total_time = scraper.total_time() or 0
            ingredients = scraper.ingredients()
            instructions = scraper.instructions_list()
            
            # Display what we found
            print(f"\n📖 Recipe Found:")
            print(f"   Title: {title}")
            print(f"   Total Time: {total_time} minutes")
            print(f"   Ingredients: {len(ingredients)} items")
            print(f"   Instructions: {len(instructions)} steps")
            
            # Insert recipe (only title and time)
            self.cursor.execute("""
                INSERT INTO recipes (name, total_time_minutes, source_url)
                VALUES (%s, %s, %s)
            """, (title, total_time, url))
            
            recipe_id = self.cursor.lastrowid
            print(f"\n  ✓ Inserted recipe (ID: {recipe_id})")
            
            # Insert ingredients
            print(f"\n  📝 Ingredients:")
            for idx, ingredient_str in enumerate(ingredients, 1):
                print(f"     {idx}. {ingredient_str}")
                ingredient_id = self.get_or_create_ingredient(ingredient_str)
                
                self.cursor.execute("""
                    INSERT INTO recipe_ingredients (recipe_id, ingredient_id, order_index)
                    VALUES (%s, %s, %s)
                """, (recipe_id, ingredient_id, idx))
            
            print(f"  ✓ Inserted {len(ingredients)} ingredients")
            
            # Insert instructions
            print(f"\n  📋 Instructions:")
            for idx, instruction in enumerate(instructions, 1):
                print(f"     Step {idx}: {instruction[:60]}...")
                self.cursor.execute("""
                    INSERT INTO instructions (recipe_id, step_number, instruction_text)
                    VALUES (%s, %s, %s)
                """, (recipe_id, idx, instruction))
            
            print(f"  ✓ Inserted {len(instructions)} instruction steps")
            
            # Commit transaction
            self.conn.commit()
            print(f"\n  ✅ Successfully added recipe to database!")
            
            return True
            
        except Exception as e:
            print(f"\n  ❌ Error: {str(e)}")
            self.conn.rollback()
            return False

    def scrape_bulk_recipes(self, urls, target_count=200):
        successful = 0
        failed = 0
        skipped = 0

        print(f" Target: {target_count} recipes")
        
        for i, url in enumerate(urls, 1):
            if successful >= target_count:
                print(f" \n Reached Target")
                break

            result = self.scrape_and_insert_recipe(url)

            if result:
                successful += 1
            elif self.recipe_exists(url):
                skipped += 1
            else: 
                failed += 1
            
            if i < len(urls):
                delay = random.uniform(2, 4)
                time.sleep(delay)

# TEST WITH SINGLE URL
if __name__ == "__main__":
    # Database configuration - UPDATE THESE!
    db_config = {
        'host': 'cooking-captain-db.c650cuym2xic.us-east-1.rds.amazonaws.com',        # or your server IP/hostname
        'user': 'admin',       # <- CHANGE THIS
        'password': 'CookingCaptain2024!',   # <- CHANGE THIS
        'database': 'recipe_db'
    }
    
    # Single test URL
    test_url = 'https://www.allrecipes.com/sheet-pan-teriyaki-glazed-pork-tenderloin-and-potatoes-recipe-11817889'
    
    # Initialize and run
    populator = RecipeDatabasePopulator(db_config)
    
    try:
        populator.connect()
        populator.scrape_and_insert_recipe(test_url)
    finally:
        populator.close()
    
    print("\n🎉 Done! Check your database to see the new recipe.")