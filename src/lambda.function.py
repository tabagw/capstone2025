"""
Cooking Captain - Alexa Skill Lambda Function
"""

import logging
from typing import Optional, Dict, List, Any, Tuple

import mysql.connector
from mysql.connector import Error
from difflib import get_close_matches

# Configure logging for debugging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Database connection parameters for AWS RDS MySQL instance
DB_CONFIG = {
    'host': 'cooking-captain-db.c650cuym2xic.us-east-1.rds.amazonaws.com',
    'user': 'admin',
    'password': 'CookingCaptain2024!',
    'database': 'recipe_db'
}

# Threshold for considering a step as a "header" 
SHORT_STEP_THRESHOLD = 25


# database 
def get_db_connection() -> Optional[mysql.connector.MySQLConnection]:
    """
    Establish a connection to the MySQL database.
    
    Creates a new database connection using the configured credentials in order
    to avoid connection pooling issues.
    
    Returns:
        A MySQL connection object
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        logger.error(f"Database connection failed: {e}")
        return None


def search_recipes_fuzzy(recipe_name: str) -> List[Tuple[int, str, float]]:
    """
    Search for recipes matching the given name using progressive matching.
    Implements a tiered search strategy:
        1. Exact match (case-insensitive)
        2. Partial match using SQL LIKE
        3. Fuzzy match using difflib for close matches

    Args:
        recipe_name: Recipe name
    
    Returns:
        A list of tuples containing recipe_id, recipe_name, confidence_score.
        Returns empty list if no matches found or on database error.
        Results are sorted by confidence (highest first).
    """
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        


        
        # Tier 1: Exact match (case-insensitive)
        cursor.execute(
            "SELECT recipe_id, name FROM recipes WHERE LOWER(name) = LOWER(%s)",
            (recipe_name,)
        )
        exact_match = cursor.fetchone()
        
        if exact_match:
            logger.info(f"Exact match found: {exact_match['name']}")
            cursor.close()
            return [(exact_match['recipe_id'], exact_match['name'], 1.0)]



        # Tier 2: Partial match using SQL LIKE
        cursor.execute(
            "SELECT recipe_id, name FROM recipes WHERE LOWER(name) LIKE LOWER(%s) LIMIT 5",
            (f"%{recipe_name}%",)
        )


        partial_matches = cursor.fetchall()
        
        if partial_matches:
            logger.info(f"Found {len(partial_matches)} partial matches")
            if len(partial_matches) == 1:
                cursor.close()
                return [(partial_matches[0]['recipe_id'], partial_matches[0]['name'], 0.9)]
            cursor.close()
            return [(r['recipe_id'], r['name'], 0.8) for r in partial_matches]
        
        # Tier 3: Fuzzy matching using difflib
        cursor.execute("SELECT recipe_id, name FROM recipes")
        all_recipes = cursor.fetchall()
        cursor.close()
        
        if not all_recipes:
            return []
        
        recipe_dict = {r['name']: r['recipe_id'] for r in all_recipes}
        recipe_names = list(recipe_dict.keys())
        
        matches = get_close_matches(recipe_name, recipe_names, n=3, cutoff=0.4)
        
        if matches:
            if len(matches) == 1:
                return [(recipe_dict[matches[0]], matches[0], 0.7)]
            return [(recipe_dict[m], m, 0.6 - i * 0.1) for i, m in enumerate(matches)]
        
        return []
        
    except Error as e:
        logger.error(f"Database error during recipe search: {e}")
        return []
    finally:
        if connection and connection.is_connected():
            connection.close()
        # yay


def get_full_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve complete recipe details including ingredients and instructions.
    
    Fetches all information needed to guide a user through cooking a recipe:
    metadata, ingredient list, and ordered cooking instructions.
    
    Args:
        recipe_id: The database ID of the recipe to retrieve.
    
    Returns:
        A dictionary containing:
            - recipe_id (int): Database ID
            - name (str): Recipe name
            - total_time_minutes (int, optional): Estimated cooking time
            - ingredients (List[str]): Formatted ingredient strings
            - instructions (List[Dict]): Step dictionaries with
              'step_number' and 'instruction_text'
        
        Returns None if recipe not found or on database error.
    """
    connection = get_db_connection()
    if not connection:
        logger.error("Failed to establish database connection")
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Fetch recipee
        cursor.execute("SELECT * FROM recipes WHERE recipe_id = %s", (recipe_id,))
        recipe = cursor.fetchone()
        

        if not recipe:
            logger.error(f"Recipe not found with ID: {recipe_id}")
            cursor.close()
            return None
        




        logger.info(f"Retrieved recipe: {recipe['name']}")
        
        # Fetch ingredients

        cursor.execute("""
            SELECT i.name
            FROM recipe_ingredients ri
            JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
            WHERE ri.recipe_id = %s
            ORDER BY ri.order_index
        """, (recipe_id,))


        ingredients_raw = cursor.fetchall()
        recipe['ingredients'] = [ing['name'] for ing in ingredients_raw]
        logger.info(f"Found {len(recipe['ingredients'])} ingredients")
        
        # Fetch cooking instructions
        
        cursor.execute("""
            SELECT step_number, instruction_text
            FROM instructions
            WHERE recipe_id = %s
            ORDER BY step_number
        """, (recipe_id,))


        recipe['instructions'] = cursor.fetchall()
        logger.info(f"Found {len(recipe['instructions'])} instruction steps")
        
        cursor.close()

        return recipe
        
    except Error as e:
        logger.error(f"Database error while fetching recipe: {e}")
        return None
    finally:
        if connection and connection.is_connected():
            connection.close()


def get_random_recipes(count: int = 3) -> List[str]:
    """
    Retrieve random recipe names for user suggestions.
    
    Args:
        count: Number of random recipes to retrieve. Defaults to 3.
    
    Returns:
        A list of recipe name strings. 
        Empty list when failure.
    """
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT name FROM recipes ORDER BY RAND() LIMIT %s", (count,))
        recipes = cursor.fetchall()
        cursor.close()
        return [r['name'] for r in recipes]
    except Error as e:
        logger.error(f"Error fetching random recipes: {e}")
        return []
    finally:
        if connection and connection.is_connected():
            connection.close()

# Instructions PROCESSING

def combine_short_steps(instructions: List[str]) -> List[str]:
    """
    Combine short header steps with their following detailed instructions.

    Args:
        instructions: List of instruction strings in order.
    
    Returns:
        New list with headers combined: "Header: Detailed instruction."
    
    Example:
        Input:  ["Preheat", "Preheat oven to 400°F."]
        Output: ["Preheat: Preheat oven to 400°F."]
    """
    if not instructions:
        return instructions
    
    combined = []
    i = 0
    
    while i < len(instructions):
        current_step = instructions[i].strip()
        
        # Check
        is_short_header = (
            len(current_step) < SHORT_STEP_THRESHOLD 
            and '.' not in current_step
        )
        
        if is_short_header and i + 1 < len(instructions):
            next_step = instructions[i + 1].strip()
            
            if len(next_step) > len(current_step):
                combined.append(f"{current_step}: {next_step}")
                i += 2  # Skip
            else:
                combined.append(current_step)
                i += 1
        else:
            combined.append(current_step)
            i += 1
    
    return combined

# intent handlers

def handle_find_recipe(event: Dict, session_attributes: Dict) -> Dict:
    """
    Handle FindRecipeIntent when user asks to find a recipe.
    
    Flow:
        1. User: "Find chocolate cake"
        2. Search database for matches
        3. Single match: Present details, ask to proceed
        4. Multiple matches: List options, ask user to choose
        5. No matches: Apologize, suggest alternatives
    
    Args:
        event: request with intent and slots.
        session_attributes: Current session state to update.
    
    Returns:
        response with speech and updated session.
    
    Session Changes (on single match):
        - conversation_state: 'confirm_recipe'
        - pending_recipe_id, pending_recipe_name
        - recipe_ingredients, recipe_instructions, total_steps
    """

    slots = event['request']['intent'].get('slots', {})
    recipe_slot = slots.get('RecipeName', {})
    recipe_name = recipe_slot.get('value', '').strip()
    
    logger.info(f"FindRecipeIntent: '{recipe_name}'")
    
    if not recipe_name:
        return build_response(
            "Sorry, I didn't catch the recipe name. What recipe would you like to find?",
            session_attributes=session_attributes
        )
    
    matches = search_recipes_fuzzy(recipe_name)
    
    # No matches
    if not matches:
        suggestions = get_random_recipes(2)


        suggest_text = f" You might like {suggestions[0]} or {suggestions[1]}." if suggestions else ""
        return build_response(
            f"Sorry, I couldn't find a recipe for {recipe_name}.{suggest_text}",
            session_attributes=session_attributes
        )
    
    
    # Single high-confidence match
    if len(matches) == 1 or matches[0][2] >= 0.9:
        recipe_id, name, confidence = matches[0]
        logger.info(f"Match: {name} (ID: {recipe_id}, conf: {confidence})")
        


        recipe = get_full_recipe(recipe_id)
        


        if recipe:
            session_attributes['pending_recipe_id'] = recipe_id
            session_attributes['pending_recipe_name'] = name
            session_attributes['conversation_state'] = 'confirm_recipe'
            session_attributes['recipe_ingredients'] = recipe.get('ingredients', [])
            session_attributes['recipe_instructions'] = [
                inst['instruction_text'] for inst in recipe.get('instructions', [])
            ]
            session_attributes['total_steps'] = len(recipe.get('instructions', []))
            


            time_text = ""
            if recipe.get('total_time_minutes'):
                time_text = f"It takes about {recipe['total_time_minutes']} minutes. "
            
            ing_count = len(recipe.get('ingredients', []))


            step_count = len(recipe.get('instructions', [])) 
            


            speak_text = (
                f"I found {name}. {time_text}"
                f"It has {ing_count} ingredients and {step_count} steps. "
                "Would you like to hear the ingredients and instructions?"
            )


            return build_response(speak_text, session_attributes=session_attributes)
        else:
            logger.error(f"Failed to load recipe ID: {recipe_id}")
            return build_response(
                f"I found {name} but couldn't load the details. Please try again.",
                session_attributes=session_attributes
            )
    
    # Multiple matches

    names = [match[1] for match in matches[:3]]

    options_text = ", ".join(names[:-1]) + f", or {names[-1]}"
    
    session_attributes['recipe_matches'] = [{'id': m[0], 'name': m[1]} for m in matches[:3]]
    session_attributes['conversation_state'] = 'choose_recipe'

    
    return build_response(
        f"I found a few recipes. Did you mean {options_text}?",
        session_attributes=session_attributes
    )



def handle_yes_intent(event: Dict, session_attributes: Dict) -> Dict:
    """
    Handle AMAZON.YesIntent for affirmative responses.
    
    Args:
        event: Alexa request event.
        session_attributes: Session state with recipe data.
    
    Returns:
        Alexa response appropriate to current state.
    """


    state = session_attributes.get('conversation_state')
    logger.info(f"YesIntent in state: {state}")
    

    if state == 'confirm_recipe':
        recipe_name = session_attributes.get('pending_recipe_name', 'this recipe')
        ingredients = session_attributes.get('recipe_ingredients', [])
        
        # if needed Reload


        if not ingredients:
            recipe_id = session_attributes.get('pending_recipe_id')
            if recipe_id:
                recipe = get_full_recipe(recipe_id)
                if recipe:
                    ingredients = recipe.get('ingredients', [])
                    session_attributes['recipe_ingredients'] = ingredients
                    session_attributes['recipe_instructions'] = [
                        inst['instruction_text'] for inst in recipe.get('instructions', [])
                    ]
                    session_attributes['total_steps'] = len(recipe.get('instructions', []))



        
        if ingredients:
            ing_text = "Here are the ingredients: "
            for ing in ingredients[:5]:
                ing_text += f"{ing}, "
            if len(ingredients) > 5:
                ing_text += f"and {len(ingredients) - 5} more. "
            else:
                ing_text = ing_text.rstrip(", ") + ". "



            ing_text += "Would you like to start the step-by-step instructions?"
        
            session_attributes['current_recipe_id'] = session_attributes.get('pending_recipe_id')
            session_attributes['current_recipe_name'] = recipe_name
            session_attributes['conversation_state'] = 'confirm_instructions'
            session_attributes['current_step'] = 0
            
            return build_response(ing_text, session_attributes=session_attributes)
        else:
            return build_response(
                "I'm having trouble loading the ingredients. Please try finding the recipe again.",
                session_attributes={}
            ) 
        
    
    elif state == 'confirm_instructions':
        instructions = session_attributes.get('recipe_instructions', [])
        
        if instructions:
            # Combine short headers
            combined_instructions = combine_short_steps(instructions)
            session_attributes['recipe_instructions'] = combined_instructions
            

            total = len(combined_instructions)
            speak_text = (
                f"Let's start cooking! Step 1 of {total}: {combined_instructions[0]} "
                "Say 'next' for the next step, or 'repeat' to hear this again."
            )
            


            session_attributes['current_step'] = 1
            session_attributes['total_steps'] = total
            session_attributes['conversation_state'] = 'cooking'
            


            return build_response(speak_text, session_attributes=session_attributes)
        else:
            return build_response(
                "I couldn't find the instructions. Please try finding the recipe again.",
                session_attributes={}
            )
        

    
    return build_response(
        "I'm not sure what you're confirming. Try asking for a recipe by name.",
        session_attributes=session_attributes
    )




def handle_no_intent(event: Dict, session_attributes: Dict) -> Dict:
    """
    Handle AMAZON.NoIntent when user declines current option.
    
    Args:
        event: Alexa request event.
        session_attributes: Session state (will be cleared).
    
    Returns:
        Alexa response offering alternatives.
    """
    suggestions = get_random_recipes(2)
    suggest_text = f" You might like {suggestions[0]} or {suggestions[1]}." if suggestions else ""
    
    return build_response(
        f"No problem! What other recipe would you like to find?{suggest_text}",
        session_attributes={}
    )



def handle_next_step(session_attributes: Dict) -> Dict:
    """
    Handle navigation to next cooking instruction step.
    
    Args:
        session_attributes: Session state with step tracking.
    
    Returns:
        Alexa response with next instruction or completion message.
    
    Requires:
        conversation_state == 'cooking'
    """
    logger.info(f"NextIntent, state: {session_attributes.get('conversation_state')}")
    
    if session_attributes.get('conversation_state') != 'cooking':
        return build_response(
            "You're not currently cooking a recipe. "
            "Try finding a recipe first by saying 'find' and the recipe name.",
            session_attributes=session_attributes
        )
    
    current_step = session_attributes.get('current_step', 0)
    total_steps = session_attributes.get('total_steps', 0)
    instructions = session_attributes.get('recipe_instructions', [])
    
    next_step = current_step + 1
    
    if next_step > total_steps or next_step > len(instructions):
        recipe_name = session_attributes.get('current_recipe_name', 'the recipe')
        return build_response(
            f"That's the last step! You've completed {recipe_name}. Enjoy your meal!",
            session_attributes={},
            should_end=True
        )
    
    session_attributes['current_step'] = next_step
    speak_text = (
        f"Step {next_step} of {total_steps}: {instructions[next_step - 1]} "
        "Say 'next' to continue, or 'repeat' to hear this again."
    )
    
    return build_response(speak_text, session_attributes=session_attributes)




def handle_repeat_step(session_attributes: Dict) -> Dict:
    """
    Handle request to repeat current cooking instruction.
    
    
    Args:
        session_attributes: Session state with step tracking.
    
    Returns:
        Alexa response with current instruction repeated.
    
    Requires:
        conversation_state == 'cooking'
    """
    logger.info(f"RepeatIntent, state: {session_attributes.get('conversation_state')}")
    
    if session_attributes.get('conversation_state') != 'cooking':
        return build_response(
            "You're not currently cooking a recipe. Try finding a recipe first.",
            session_attributes=session_attributes
        )
    
    current_step = session_attributes.get('current_step', 1)
    total_steps = session_attributes.get('total_steps', 0)
    instructions = session_attributes.get('recipe_instructions', [])
    
    if 0 < current_step <= len(instructions):
        speak_text = (
            f"Step {current_step} of {total_steps}: {instructions[current_step - 1]} "
            "Say 'next' to continue."
        )
        return build_response(speak_text, session_attributes=session_attributes)
    
    return build_response(
        "I couldn't find that step. Please try finding the recipe again.",
        session_attributes={}
    )




def handle_previous_step(session_attributes: Dict) -> Dict:
    """
    Handle navigation to previous cooking instruction step.
    
    Moves back one step. If already at step 1, informs user.
    
    Args:
        session_attributes: Session state with step tracking.
    
    Returns:
        Alexa response with previous instruction.
    
    Requires:
        conversation_state == 'cooking'
    """
    logger.info(f"PreviousIntent, state: {session_attributes.get('conversation_state')}")
    
    if session_attributes.get('conversation_state') != 'cooking':
        return build_response(
            "You're not currently cooking a recipe. Try finding a recipe first.",
            session_attributes=session_attributes
        )
    
    current_step = session_attributes.get('current_step', 1)
    total_steps = session_attributes.get('total_steps', 0)
    instructions = session_attributes.get('recipe_instructions', [])
    
    if current_step <= 1:
        speak_text = (
            f"You're already at step 1: {instructions[0]} "
            "Say 'next' to continue."
        )
        return build_response(speak_text, session_attributes=session_attributes)
    


    prev_step = current_step - 1
    session_attributes['current_step'] = prev_step
    


    speak_text = (
        f"Going back. Step {prev_step} of {total_steps}: {instructions[prev_step - 1]} "
        "Say 'next' to continue."
    )
    
    return build_response(speak_text, session_attributes=session_attributes)




def handle_help(session_attributes: Dict) -> Dict:
    """
    Handle AMAZON.HelpIntent to provide usage guidance.
    
    Args:
        session_attributes: Session state (preserved).
    
    Returns:
        Alexa response with help information.
    """


    suggestions = get_random_recipes(2)
    suggest_text = f" For example, try 'find {suggestions[0]}'." if suggestions else ""
    

    help_text = (
        "I can help you find and cook recipes! "
        "Ask for a recipe by name, like 'find chocolate cake'. "
        "When cooking, say 'next' for the next step, 'repeat' to hear it again, "
        "or 'previous' to go back."
        f"{suggest_text}"
    )
    
    return build_response(help_text, session_attributes=session_attributes)

def build_response(
    speech_text: str,
    session_attributes: Optional[Dict] = None,
    should_end: bool = False
) -> Dict:
    """
    Builds a properly formatted Alexa skill response.
    """
    if session_attributes is None:
        session_attributes = {}
    
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": speech_text
            },
            "shouldEndSession": should_end,
            "reprompt": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "What would you like to do? Say 'next' for the next step, or ask for another recipe."
                }
            }
        }
    }

def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Main entry point for AWS Lambda function.
    
    Invoked by Alexa for every user interaction. Routes requests
    to appropriate handlers based on request type and intent.
    """
    request_type = event['request']['type']
    session_attributes = event.get('session', {}).get('attributes', {}) or {}
    


    logger.info(f"Request: {request_type}, State: {session_attributes.get('conversation_state', 'none')}")
    
    # Skill launch
    if request_type == "LaunchRequest":
        suggestions = get_random_recipes(3)
        suggest_text = ""
        if suggestions:
            suggest_text = f" Try asking for {suggestions[0]}, {suggestions[1]}, or {suggestions[2]}."
        

        welcome_text = (
            "Welcome to Cooking Captain! I can help you find recipes from my database. "
            "Ask for a recipe by name, or search by ingredient."
            f"{suggest_text}"
        )
        return build_response(welcome_text, session_attributes=session_attributes)



    # Intent request
    elif request_type == "IntentRequest":
        intent_name = event['request']['intent']['name']
        logger.info(f"Intent: {intent_name}")
        
        if intent_name == "FindRecipeIntent":
            return handle_find_recipe(event, session_attributes)
        
        elif intent_name == "AMAZON.YesIntent":
            return handle_yes_intent(event, session_attributes)
        
        elif intent_name == "AMAZON.NoIntent":
            return handle_no_intent(event, session_attributes)
        
        elif intent_name in ["NextIntent", "AMAZON.NextIntent"]:
            return handle_next_step(session_attributes)
        
        elif intent_name in ["RepeatIntent", "AMAZON.RepeatIntent"]:
            return handle_repeat_step(session_attributes)
        
        elif intent_name in ["PreviousIntent", "AMAZON.PreviousIntent"]:
            return handle_previous_step(session_attributes)
        
        elif intent_name == "AMAZON.HelpIntent":
            return handle_help(session_attributes)
        
        elif intent_name in ["AMAZON.CancelIntent", "AMAZON.StopIntent"]:
            return build_response("Happy cooking! Goodbye!", should_end=True)
        
        elif intent_name == "AMAZON.FallbackIntent":
            if session_attributes.get('conversation_state') == 'cooking':
                return build_response(
                    "I didn't catch that. Say 'next' for the next step, "
                    "'repeat' to hear it again, or 'stop' to end.",
                    session_attributes=session_attributes
                )
            return build_response(
                "I'm not sure about that. Try asking for a recipe by name, like 'find pasta'.",
                session_attributes=session_attributes
            )
        
        else:
            logger.warning(f"Unhandled intent: {intent_name}")
            return build_response(
                "I didn't understand that. Try asking for a recipe by name.",
                session_attributes=session_attributes
            )
    
    # Session ended or other
    else:
        return build_response("Goodbye!", should_end=True)


__all__ = ['lambda_handler']