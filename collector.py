"""
Automatically collect recipe URLs from recipe sites
Save URLs to a text file for later use
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import json

class RecipeURLCollector:
    """Collects recipe URLs from recipe sites"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def get_allrecipes_urls(self, num_urls=100):
        """Collect URLs from AllRecipes category pages"""
        urls = []
        categories = [
            'https://www.allrecipes.com/recipes/201/meat-and-poultry/chicken/',
            'https://www.allrecipes.com/recipes/79/desserts/',
            'https://www.allrecipes.com/recipes/17562/dinner/',
            'https://www.allrecipes.com/recipes/78/breakfast-and-brunch/',
            'https://www.allrecipes.com/recipes/96/salad/',
            'https://www.allrecipes.com/recipes/156/bread/',
            'https://www.allrecipes.com/recipes/95/pasta-and-noodles/',
            'https://www.allrecipes.com/recipes/80/main-dish/',
        ]
        
        print("📥 Collecting AllRecipes URLs...")
        for category_url in categories:
            if len(urls) >= num_urls:
                break
            try:
                response = requests.get(category_url, headers=self.headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find recipe links (AllRecipes uses specific link patterns)
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if '/recipe/' in href and href.startswith('https://www.allrecipes.com/recipe/'):
                        if href not in urls:
                            urls.append(href)
                            if len(urls) >= num_urls:
                                break
                
                print(f"  Found {len(urls)} URLs so far...")
                time.sleep(2)  # Be polite
                
            except Exception as e:
                print(f"  ⚠️  Error collecting from {category_url}: {e}")
        
        return urls[:num_urls]
    
    def get_foodnetwork_urls(self, num_urls=50):
        """Collect URLs from Food Network"""
        urls = []
        search_pages = [
            'https://www.foodnetwork.com/recipes/recipes-a-z/123',
            'https://www.foodnetwork.com/recipes/recipes-a-z/a',
            'https://www.foodnetwork.com/recipes/recipes-a-z/b',
            'https://www.foodnetwork.com/recipes/recipes-a-z/c',
        ]
        
        print("📥 Collecting Food Network URLs...")
        for page_url in search_pages:
            if len(urls) >= num_urls:
                break
            try:
                response = requests.get(page_url, headers=self.headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if '/recipes/' in href and href.startswith('/recipes/'):
                        full_url = urljoin('https://www.foodnetwork.com', href)
                        if full_url not in urls and '-recipe-' in full_url:
                            urls.append(full_url)
                            if len(urls) >= num_urls:
                                break
                
                print(f"  Found {len(urls)} URLs so far...")
                time.sleep(2)
                
            except Exception as e:
                print(f"  ⚠️  Error: {e}")
        
        return urls[:num_urls]
    
    def get_bbcgoodfood_urls(self, num_urls=50):
        """Collect URLs from BBC Good Food"""
        urls = []
        categories = [
            'https://www.bbcgoodfood.com/recipes/category/dishes',
            'https://www.bbcgoodfood.com/recipes/category/cuisines',
            'https://www.bbcgoodfood.com/recipes/category/ingredients',
        ]
        
        print("📥 Collecting BBC Good Food URLs...")
        for category_url in categories:
            if len(urls) >= num_urls:
                break
            try:
                response = requests.get(category_url, headers=self.headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if '/recipes/' in href:
                        if not href.startswith('http'):
                            href = urljoin('https://www.bbcgoodfood.com', href)
                        if href not in urls and '/recipes/' in href:
                            urls.append(href)
                            if len(urls) >= num_urls:
                                break
                
                print(f"  Found {len(urls)} URLs so far...")
                time.sleep(2)
                
            except Exception as e:
                print(f"  ⚠️  Error: {e}")
        
        return urls[:num_urls]
    
    def save_urls_to_file(self, urls, filename='recipe_urls.txt'):
        """Save URLs to a text file"""
        with open(filename, 'w') as f:
            for url in urls:
                f.write(url + '\n')
        print(f"\n💾 Saved {len(urls)} URLs to {filename}")
    
    def save_urls_to_json(self, urls, filename='recipe_urls.json'):
        """Save URLs to a JSON file with metadata"""
        data = {
            'total_urls': len(urls),
            'urls': urls
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Saved {len(urls)} URLs to {filename}")


if __name__ == "__main__":
    print("=" * 80)
    print("RECIPE URL COLLECTOR")
    print("=" * 80)
    
    collector = RecipeURLCollector()
    all_urls = []
    
    # Collect from different sites
    all_urls.extend(collector.get_allrecipes_urls(num_urls=120))
    all_urls.extend(collector.get_foodnetwork_urls(num_urls=50))
    all_urls.extend(collector.get_bbcgoodfood_urls(num_urls=50))
    
    # Remove duplicates
    all_urls = list(set(all_urls))
    
    print(f"\n✅ Collected {len(all_urls)} unique recipe URLs")
    
    # Save to files
    collector.save_urls_to_file(all_urls, 'recipe_urls.txt')
    collector.save_urls_to_json(all_urls, 'recipe_urls.json')
    
    print("\n🎉 URL collection complete!")
    print("Next step: Run database_populator.py to scrape and add recipes to database")