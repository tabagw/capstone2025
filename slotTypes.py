"""
Sync recipe names from MySQL database to Alexa Skill slot type
"""

import mysql.connector
import json
import requests
from typing import List, Dict

class AlexaSlotSync:
    def __init__(self, db_config, alexa_config):
        """
        db_config = {
            'host': 'cooking-captain-db.c650cuym2xic.us-east-1.rds.amazonaws.com',
            'user': 'admin',
            'password': 'CookingCaptain2024!',
            'database': 'recipe_db'
        }
        
        alexa_config = {
            'skill_id': 'amzn1.ask.skill.5058ab8f-876e-425f-ab32-f094f7842fe9',
            'stage': 'development'
            'access_token': 'Atza|gQBdtJUoAwEBAIctd_TEjdLeolTuMyHXFXr4nK4ZanRnURT7zJh7Z2vbOE6YGxoceFkjWK3YdjiDRpA1ASx1BYEoCZBpeaubECVR4fU13jBWjEKF3ZImuJtseeMB_yf0ic_8L7Ht0rsGyeX9T4Lzw5aCA6CP8wMctVDP-Ad_Aba2nEb5Wfa9FemyQXSx6Gujyyoit8qpXKgiMuN51OJimOKFRhlOd_O9oNTn_rfscy4UNwEJW23U4T2jx8DzIgddOvW6Yz-R-dd6h99krz4pWetul3gOvCOTpDl21MC6Ef8YpuQJMFhGiUz5bRWbwwXLyRgkhHQe1QjgL1av4NInj0mlrSQwUIaDnu-BC9HobXUgNvafRkXlJnes9Po2mTS8L7SOczsefg443anZ1kwIUnjzi0msUqGM2MLBt80DFBQG1VIMljY3YIaJGSqPCimbpS0jD6O37usz3R1exLlQaaej3SVqdm3oQBopJPyVAewZYHh8rKtfCju5FY1jEjRFedi42geZFsrl9SnPb-_Fd9vizoQ77GAB9JQu3gcnVLEdqXDVhW8k8GIhM1Ww8cLa3-wEuOCQcqOqXIegK_HST3Nc6sc_1q9tqWD3phtq482FyDZwk7xxZvP2BEyW7xxiE5nsXZpPjiSoJt1EiUI02x9KcxSqMcVvFgBWRSJIZv1AgOJaZYzjxjdSP4GFZSA0xejJJpRrZktT4vvWAcGXU5G367m2TRbMb6zr8LV2s5PVBg9_BHItK-8NCDobUXKTDA",
        }
        """
        self.db_config = db_config
        self.alexa_config = alexa_config
        self.conn = None
        self.cursor = None
    
    def connect_db(self):
        """Connect to MySQL database"""
        self.conn = mysql.connector.connect(**self.db_config)
        self.cursor = self.conn.cursor(dictionary=True)
        print("✓ Connected to database")
    
    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✓ Database connection closed")
    
    def get_all_recipe_names(self) -> List[Dict]:
        """Get all recipe names from database"""
        self.cursor.execute("SELECT recipe_id, name FROM recipes ORDER BY name")
        recipes = self.cursor.fetchall()
        print(f"✓ Found {len(recipes)} recipes in database")
        return recipes
    
    def format_for_alexa_slot(self, recipes: List[Dict]) -> List[Dict]:
        """
        Format recipe names for Alexa slot type
        Creates variations and synonyms for better recognition
        """
        slot_values = []
        
        for recipe in recipes:
            recipe_name = recipe['name']
            recipe_id = recipe['recipe_id']
            
            # Main slot value
            slot_value = {
                "id": str(recipe_id),
                "name": {
                    "value": recipe_name,
                    "synonyms": self._generate_synonyms(recipe_name)
                }
            }
            
            slot_values.append(slot_value)
        
        print(f"✓ Formatted {len(slot_values)} slot values")
        return slot_values
    
    def _generate_synonyms(self, recipe_name: str) -> List[str]:
        """
        Generate common variations of recipe name for better matching
        e.g., "Chocolate Chip Cookies" -> ["chocolate chip cookie", "choco chip cookies"]
        """
        synonyms = []
        name_lower = recipe_name.lower()
        
        # Remove common suffixes/prefixes
        variations = [
            name_lower,
            name_lower.replace(" recipe", ""),
            name_lower.replace("the ", ""),
            name_lower.replace("best ", ""),
            name_lower.replace("easy ", ""),
        ]
        
        # Add singular/plural variations
        if name_lower.endswith('s'):
            variations.append(name_lower[:-1])  # Remove 's'
        else:
            variations.append(name_lower + 's')  # Add 's'
        
        # Remove duplicates and original name
        synonyms = list(set(v for v in variations if v and v != name_lower))
        
        return synonyms[:5]  # Limit to 5 synonyms
    
    def export_to_json(self, slot_values: List[Dict], filename='alexa_recipe_slot.json'):
        """Export slot values to JSON file for manual upload"""
        slot_type = {
            "interactionModel": {
                "languageModel": {
                    "types": [
                        {
                            "name": "RecipeName",
                            "values": slot_values
                        }
                    ]
                }
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(slot_type, f, indent=2)
        
        print(f"✓ Exported to {filename}")
        print(f"\nTo upload manually:")
        print(f"1. Go to Alexa Developer Console")
        print(f"2. Open your skill > Build > Interaction Model")
        print(f"3. Go to Slot Types > RecipeName")
        print(f"4. Import the values from {filename}")
    
    def export_simple_list(self, recipes: List[Dict], filename='recipe_list.txt'):
        """Export simple list of recipe names (for copy-paste into Alexa console)"""
        with open(filename, 'w') as f:
            for recipe in recipes:
                f.write(f"{recipe['name']}\n")
        
        print(f"✓ Exported simple list to {filename}")
        print(f"You can copy-paste these directly into the Alexa Developer Console")
    
    def sync_to_alexa_api(self, slot_values: List[Dict]):
        """
        Sync slot values to Alexa using the SMAPI (Skill Management API)
        Requires OAuth token from Alexa Developer Console
        """
        skill_id = self.alexa_config['skill_id']
        stage = self.alexa_config['stage']
        access_token = self.alexa_config['access_token']
        
        # SMAPI endpoint
        url = f"https://api.amazonalexa.com/v1/skills/{skill_id}/stages/{stage}/interactionModel/locales/en-US"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Build interaction model with slot type
        interaction_model = {
            "interactionModel": {
                "languageModel": {
                    "invocationName": "cooking captain",  # Change this to your skill's invocation name
                    "types": [
                        {
                            "name": "RecipeName",
                            "values": slot_values
                        }
                    ],
                    "intents": [
                        # Add your existing intents here
                    ]
                }
            }
        }
        
        try:
            response = requests.put(url, headers=headers, json=interaction_model)
            
            if response.status_code == 202:
                print("✅ Successfully synced to Alexa!")
                print(f"Build ID: {response.headers.get('Location')}")
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error syncing to Alexa: {e}")


# USAGE EXAMPLES
if __name__ == "__main__":
    # Database configuration
    db_config = {
        'host': 'cooking-captain-db.c650cuym2xic.us-east-1.rds.amazonaws.com',
        'user': 'admin',
        'password': 'CookingCaptain2024!',
        'database': 'recipe_db'
    }
    
    # Alexa configuration (optional - only needed for API sync)
    alexa_config = {
        'skill_id': 'amzn1.ask.skill.xxxxx',  # Your skill ID
        'stage': 'development',
        'access_token': 'your-oauth-token'  # Get from Alexa Developer Console
    }
    
    # Initialize syncer
    syncer = AlexaSlotSync(db_config, alexa_config)
    
    try:
        # Connect to database
        syncer.connect_db()
        
        # Get all recipes
        recipes = syncer.get_all_recipe_names()
        
        # Format for Alexa
        slot_values = syncer.format_for_alexa_slot(recipes)
        
        # Export options:
        
        # Option 1: Export to JSON for manual upload
        syncer.export_to_json(slot_values, 'alexa_recipe_slot.json')
        
        # Option 2: Export simple text list
        syncer.export_simple_list(recipes, 'recipe_list.txt')
        
        # Option 3: Sync directly via API (requires OAuth token)
        # syncer.sync_to_alexa_api(slot_values)
        
    finally:
        syncer.close_db()
    
    print("\n✅ Done!")