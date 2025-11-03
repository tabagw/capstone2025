"""
Recipe Database Populator
Reads URLs from file and scrapes recipes into MySQL database
"""

import mysql.connector
from recipe_scrapers import scrape_me
import time
import random
import json

class RecipeDatabasePopulator:
    def __init__(self, db_config):
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
        """Check if recipe URL already exists in database"""
        self.cursor.execute(
            "SELECT recipe_id FROM recipes WHERE source_url = %s",
            (url,)
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
            # Check if already exists
            if self.recipe_exists(url):
                print(f"⏭️  Recipe already exists, skipping")
                return False
            
            print(f"\n📥 Scraping: {url}")
            
            # Scrape the recipe
            scraper = scrape_me(url)
            
            # Get the data
            title = scraper.title()
            total_time = scraper.total_time() or 0
            ingredients = scraper.ingredients()
            instructions = scraper.instructions_list()
            
            # Validate we got meaningful data
            if not title or not ingredients or not instructions:
                print(f"  ⚠️  Incomplete recipe data, skipping")
                return False
            
            # Display what we found
            print(f"   Title: {title}")
            print(f"   Time: {total_time} min | Ingredients: {len(ingredients)} | Steps: {len(instructions)}")
            
            # Insert recipe
            self.cursor.execute("""
                INSERT INTO recipes (name, total_time_minutes, source_url)
                VALUES (%s, %s, %s)
            """, (title, total_time, url))
            
            recipe_id = self.cursor.lastrowid
            
            # Insert ingredients
            for idx, ingredient_str in enumerate(ingredients, 1):
                ingredient_id = self.get_or_create_ingredient(ingredient_str)
                self.cursor.execute("""
                    INSERT INTO recipe_ingredients (recipe_id, ingredient_id, order_index)
                    VALUES (%s, %s, %s)
                """, (recipe_id, ingredient_id, idx))
            
            # Insert instructions
            for idx, instruction in enumerate(instructions, 1):
                self.cursor.execute("""
                    INSERT INTO instructions (recipe_id, step_number, instruction_text)
                    VALUES (%s, %s, %s)
                """, (recipe_id, idx, instruction))
            
            # Commit transaction
            self.conn.commit()
            print(f"  ✅ Successfully added recipe (ID: {recipe_id})")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.conn.rollback()
            return False

    def bulk_scrape_recipes(self, urls, target_count=200):
        """Scrape multiple recipes from a list of URLs"""
        successful = 0
        failed = 0
        skipped = 0
        
        print(f"\n🎯 Target: {target_count} recipes")
        print(f"📋 Processing {len(urls)} URLs\n")
        print("=" * 80)
        
        for i, url in enumerate(urls, 1):
            if successful >= target_count:
                print(f"\n🎉 Reached target of {target_count} recipes!")
                break
            
            print(f"\n[{i}/{len(urls)}] Progress: {successful} added, {failed} failed, {skipped} skipped")
            
            result = self.scrape_and_insert_recipe(url)
            
            if result:
                successful += 1
            elif self.recipe_exists(url):
                skipped += 1
            else:
                failed += 1
            
            # Be polite to servers - add delay between requests
            if i < len(urls):
                delay = random.uniform(2, 5)
                time.sleep(delay)
        
        print("\n" + "=" * 80)
        print(f"\n📊 Final Statistics:")
        print(f"   ✅ Successfully added: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏭️  Skipped (duplicates): {skipped}")
        print(f"   📈 Total processed: {successful + failed + skipped}")
    
    def load_urls_from_file(self, filename='recipe_urls.txt'):
        """Load URLs from a text file"""
        urls = []
        try:
            with open(filename, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            print(f"✓ Loaded {len(urls)} URLs from {filename}")
        except FileNotFoundError:
            print(f"❌ File not found: {filename}")
        return urls
    
    def load_urls_from_json(self, filename='recipe_urls.json'):
        """Load URLs from a JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            urls = data.get('urls', [])
            print(f"✓ Loaded {len(urls)} URLs from {filename}")
            return urls
        except FileNotFoundError:
            print(f"❌ File not found: {filename}")
            return []


if __name__ == "__main__":
    print("=" * 80)
    print("RECIPE DATABASE POPULATOR")
    print("=" * 80)
    
    # Database configuration
    db_config = {
        'host': 'cooking-captain-db.c650cuym2xic.us-east-1.rds.amazonaws.com',
        'user': 'admin',
        'password': 'CookingCaptain2024!',
        'database': 'recipe_db'
    }
    
    # Initialize populator
    populator = RecipeDatabasePopulator(db_config)
    
    # Load URLs from file (try JSON first, then fall back to TXT)
    urls = populator.load_urls_from_json('recipe_urls.json')
    if not urls:
        urls = populator.load_urls_from_file('recipe_urls.txt')
    
    if not urls:
        print("\n❌ No URLs found! Please run url_collector.py first.")
        exit(1)
    
    # Connect and populate database
    try:
        populator.connect()
        populator.bulk_scrape_recipes(urls, target_count=200)
    finally:
        populator.close()
    
    print("\n🎉 All done! Check your database.")