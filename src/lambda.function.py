# -*- coding: utf-8 -*-

import logging
import json
import os
import urllib.request
import pymysql
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from recipe_scrapers import scrape_html

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Database Configuration
DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME', 'recipe_db')

def get_db_connection():
    """Create database connection"""
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connect_timeout=5
        )
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def init_database():
    """Initialize database tables if they don't exist"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255),
                    name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create recipes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    recipe_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255),
                    recipe_url TEXT NOT NULL,
                    title VARCHAR(500),
                    total_time INT,
                    servings INT,
                    ingredients TEXT,
                    instructions TEXT,
                    nutrients TEXT,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            connection.commit()
            logger.info("Database initialized successfully")
            return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    finally:
        connection.close()

def create_or_get_user(user_id, email=None, name=None):
    """Create or retrieve user from database"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                # Create new user
                cursor.execute(
                    "INSERT INTO users (user_id, email, name) VALUES (%s, %s, %s)",
                    (user_id, email, name)
                )
                connection.commit()
                logger.info(f"Created new user: {user_id}")
            
            return user_id
    except Exception as e:
        logger.error(f"Error managing user: {e}")
        return None
    finally:
        connection.close()

def save_recipe(user_id, recipe_url, scraper_data):
    """Save scraped recipe to database"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO recipes 
                (user_id, recipe_url, title, total_time, servings, ingredients, 
                 instructions, nutrients, image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                recipe_url,
                scraper_data.get('title'),
                scraper_data.get('total_time'),
                scraper_data.get('servings'),
                json.dumps(scraper_data.get('ingredients', [])),
                json.dumps(scraper_data.get('instructions', [])),
                json.dumps(scraper_data.get('nutrients', {})),
                scraper_data.get('image')
            ))
            connection.commit()
            recipe_id = cursor.lastrowid
            logger.info(f"Saved recipe {recipe_id} for user {user_id}")
            return recipe_id
    except Exception as e:
        logger.error(f"Error saving recipe: {e}")
        return None
    finally:
        connection.close()

def get_user_recipes(user_id):
    """Retrieve all recipes for a user"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM recipes WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            recipes = cursor.fetchall()
            return recipes
    except Exception as e:
        logger.error(f"Error fetching recipes: {e}")
        return []
    finally:
        connection.close()

def scrape_recipe(url):
    """Scrape recipe from URL"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            html = response.read().decode("utf-8")
        
        scraper = scrape_html(html, org_url=url)
        
        # Extract data
        recipe_data = {
            'title': scraper.title(),
            'total_time': scraper.total_time(),
            'servings': scraper.yields(),
            'ingredients': scraper.ingredients(),
            'instructions': scraper.instructions_list(),
            'nutrients': scraper.nutrients(),
            'image': scraper.image() if hasattr(scraper, 'image') else None,
            'url': url
        }
        
        return recipe_data
    except Exception as e:
        logger.error(f"Error scraping recipe: {e}")
        return None

# Initialize database on cold start
init_database()


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch"""
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        user_id = handler_input.request_envelope.session.user.user_id
        create_or_get_user(user_id)
        
        speak_output = """Welcome to Cooking Captain! You can ask me to save a recipe 
        by saying 'save recipe' followed by the URL, or ask about your saved recipes. 
        What would you like to do?"""
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("What would you like to do?")
                .response
        )


class AddRecipeIntentHandler(AbstractRequestHandler):
    """Handler for adding a new recipe"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AddRecipeIntent")(handler_input)

    def handle(self, handler_input):
        user_id = handler_input.request_envelope.session.user.user_id
        
        # Get recipe URL from slot
        slots = handler_input.request_envelope.request.intent.slots
        recipe_url = slots.get("RecipeURL")
        
        if not recipe_url or not recipe_url.value:
            speak_output = "I didn't catch the recipe URL. Please say 'save recipe' followed by the full URL."
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask(speak_output)
                    .response
            )
        
        url = recipe_url.value
        
        # Scrape the recipe
        recipe_data = scrape_recipe(url)
        
        if not recipe_data:
            speak_output = f"Sorry, I couldn't scrape the recipe from that URL. Please make sure it's a valid recipe website."
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask("Would you like to try another recipe?")
                    .response
            )
        
        # Save to database
        recipe_id = save_recipe(user_id, url, recipe_data)
        
        if recipe_id:
            speak_output = f"Great! I've saved {recipe_data['title']} to your collection. You can ask me about ingredients, instructions, or cooking time."
        else:
            speak_output = "I scraped the recipe but had trouble saving it. Please try again."
        
        # Store current recipe in session
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['current_recipe'] = recipe_data
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("What would you like to know about this recipe?")
                .response
        )


class ListRecipesIntentHandler(AbstractRequestHandler):
    """Handler for listing user's recipes"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ListRecipesIntent")(handler_input)

    def handle(self, handler_input):
        user_id = handler_input.request_envelope.session.user.user_id
        recipes = get_user_recipes(user_id)
        
        if not recipes:
            speak_output = "You don't have any saved recipes yet. Say 'save recipe' followed by a URL to add one!"
        else:
            recipe_titles = [recipe['title'] for recipe in recipes[:5]]
            speak_output = f"You have {len(recipes)} saved recipes. Here are your most recent: {', '.join(recipe_titles)}"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("Would you like to hear details about any of these recipes?")
                .response
        )


class GetIngredientsIntentHandler(AbstractRequestHandler):
    """Handler for getting ingredients"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("GetIngredientsIntent")(handler_input)

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        recipe = session_attr.get('current_recipe')
        
        if not recipe:
            speak_output = "I don't have a recipe loaded. Please add a recipe first by saying 'save recipe' followed by the URL."
        else:
            ingredients = recipe.get('ingredients', [])
            speak_output = f"Here are the ingredients for {recipe['title']}: {', '.join(ingredients[:10])}"
            
            if len(ingredients) > 10:
                speak_output += f" and {len(ingredients) - 10} more."
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("What else would you like to know?")
                .response
        )


class GetInstructionsIntentHandler(AbstractRequestHandler):
    """Handler for getting cooking instructions"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("GetInstructionsIntent")(handler_input)

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        recipe = session_attr.get('current_recipe')
        
        if not recipe:
            speak_output = "I don't have a recipe loaded. Please add a recipe first."
        else:
            instructions = recipe.get('instructions', [])
            if isinstance(instructions, list):
                speak_output = f"Here are the instructions for {recipe['title']}: " + " ".join(instructions[:3])
            else:
                speak_output = f"Here are the instructions: {instructions[:500]}"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("Would you like to hear more?")
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = """You can save recipes by saying 'save recipe' followed by the URL. 
        You can also ask to list your recipes, get ingredients, or get cooking instructions."""
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Handler for Cancel and Stop Intent"""
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        speak_output = "Happy cooking!"
        return handler_input.response_builder.speak(speak_output).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End"""
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling"""
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        speak_output = "Sorry, I had trouble doing what you asked. Please try again."
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


# Build skill
sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(AddRecipeIntentHandler())
sb.add_request_handler(ListRecipesIntentHandler())
sb.add_request_handler(GetIngredientsIntentHandler())
sb.add_request_handler(GetInstructionsIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()


# API Gateway handler for direct API calls (testing with Postman)
def api_handler(event, context):
    """
    Handle direct API calls for testing with Postman
    """
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        
        if action == 'scrape_recipe':
            url = body.get('url')
            recipe_data = scrape_recipe(url)
            return {
                'statusCode': 200,
                'body': json.dumps(recipe_data),
                'headers': {'Content-Type': 'application/json'}
            }
        
        elif action == 'save_recipe':
            user_id = body.get('user_id')
            url = body.get('url')
            recipe_data = scrape_recipe(url)
            if recipe_data:
                recipe_id = save_recipe(user_id, url, recipe_data)
                return {
                    'statusCode': 200,
                    'body': json.dumps({'recipe_id': recipe_id, 'data': recipe_data}),
                    'headers': {'Content-Type': 'application/json'}
                }
        
        elif action == 'get_recipes':
            user_id = body.get('user_id')
            recipes = get_user_recipes(user_id)
            return {
                'statusCode': 200,
                'body': json.dumps(recipes, default=str),
                'headers': {'Content-Type': 'application/json'}
            }
        
        elif action == 'create_user':
            user_id = body.get('user_id')
            email = body.get('email')
            name = body.get('name')
            create_or_get_user(user_id, email, name)
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'User created', 'user_id': user_id}),
                'headers': {'Content-Type': 'application/json'}
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid action'}),
                'headers': {'Content-Type': 'application/json'}
            }
    
    except Exception as e:
        logger.error(f"API Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {'Content-Type': 'application/json'}
        }