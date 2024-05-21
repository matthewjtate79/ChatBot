import os
from dotenv import load_dotenv
from openai import OpenAI
import subprocess

load_dotenv()

client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY")
)

game_names = {"sekiro": "Sekiro: Shadows Die Twice", "callofdutymw3": "Call of Duty: Modern Warfare 3", "leagueoflegends": "League of Legends",
              "eldenring": "Elden Ring"}


def ExtractPredicates(client, user_prompt):
    model = "gpt-3.5-turbo"
    system_prompt = "You are a semantic parser, whose job is to extract logical predicates from a given sentence in the user prompt.\n" \
                    "List of allowed predicates to extract:\n" \
                    "pov(Game,X), where X can be firstperson, thirdperson, or birdview.\n" \
                    "genre(Game,X), where X can be soulslike, shooter, roguelike, mmo, fighting, jrpg, or moba.\n" \
                    "setting(Game,X), where X can be fantasy, warzone, horror, post-apocalyptic, futuristic, or historical.\n" \
                    "platform(Game,X), where X can be xbox, playstation, pc, switch, or mobile.\n" \
                    "num_players(Game,X), where X can be singleplayer or multiplayer.\n" \
                    "price(Game,X), where X can be cheap (less than $50 / not AAA) or expensive ($50-$70).\n\n" \
                    "Below are some examples:\n" \
                    "Input: Hi, I'm looking for a some kind of singleplayer shooter game that's set in a futuristic setting. Output: genre(Game,shooter), setting(Game,futuristic), num_players(Game,singleplayer)\n" \
                    "Input: I'm on a budget right now, so I'd prefer something under $40. I'm mainly interested in games similar to dark souls. Output: genre(Game,soulslike), price(Game,cheap)\n" \
                    "Input: num_players(Game,X)? Both. Output: num_players(Game,singleplayer), num_players(Game,multiplayer)"
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return completion.choices[0].message


def GenerateRecommendation(client, user_prompt):
    model = "gpt-3.5-turbo"
    system_prompt = "You are a video game recommender chatbot. At this point, the actual program generating the recommendation has returned an actual game name, and your task is to recommend it to the user.\n" \
                    "Do not use outside knowledge, as you may get games mixed up or make incorrect statements about the game itself.\n" \
                    "Example: Input: 'Stellar Blade'. Output: Based on your preferences, I would recommend Stellar Blade."
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return completion.choices[0].message

def GenerateResponse(client, user_prompt):
    model = "gpt-3.5-turbo"
    system_prompt = "You are a video game recommender chatbot, whose job is to generate questions requesting extra information. You will be given a logical predicate that represents the missing information.\n" \
                    "Note that 'Game' within the predicate is simply a placeholder for the actual recommendation. 'Y' represents their preference for that predicate.\n" \
                    "For example: num_players(Game,Y) represents whether or not the user wants singleplayer or multiplayer."
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return completion.choices[0].message

def RunScasp(query):
    # Create a new text file with the query at the end for s(casp)
    lines = None
    with open("games.txt", "r") as f:
        lines = f.readlines()
        lines.append(query)

    with open("scaspProgram.txt", "w") as f:
        f.writelines(lines)

    # Runs s(casp) program and gets the first model as the output
    scasp_command = "scasp scaspProgram.txt -s1"
    output = subprocess.check_output(scasp_command, shell=True, text=True)

    # Extracts assignment to Game from s(casp) output
    recommendation = None
    lines = output.splitlines()

    for line in lines:
        if line.startswith("Game ="):
            recommendation = line.split("=")[1].strip()

    return recommendation

def FindRecommendation(client):
    # Maintains a list of all six categories to check if we have missing information
    all_categories = ["pov", "genre", "setting", "platform", "num_players", "price"]

    # Gets the user's initial sentence of what they want in a game
    preferences = input("Hello. How can I assist you today?\n")

    # Uses gpt-3.5 to extract the predicates from the user's sentence
    predicates = ExtractPredicates(client, preferences).content.split(", ")
    # Checks what categories of preferences we have so far
    categories = [predicate.split("(")[0] for predicate in predicates]

    # Checks what categories we have not gotten the user's preference for yet
    for category in all_categories:
        if category not in categories:
            # Uses gpt-3.5 to ask the user for the missing category preference
            new_prompt = category + "(Game,X)"
            new_question = GenerateResponse(client, new_prompt).content

            # Gets the user's response to question and uses gpt-3.5 to extract the predicate(s)
            user_response = input(new_question + "\n")
            new_predicates = ExtractPredicates(client, new_prompt + "? " + user_response).content.split(", ")

            # Updates list of predicates and satisfied categories
            predicates = predicates + new_predicates
            categories = [predicate.split("(")[0] for predicate in predicates]

    # Converts the final list of predicates into a query to put into s(casp) program
    scasp_query = "?- "
    for i in range(0, len(predicates)):
        scasp_query += predicates[i]
        if i < (len(predicates) - 1):
            scasp_query += ", "
        else:
            scasp_query += "."

    # Runs the s(casp) program and extracts the video game recommendation from the model
    recommendation = RunScasp(scasp_query)
    if recommendation is not None:
        game_name = game_names[recommendation]

        # Uses gpt-3.5 to give the user the final recommendation.
        final_chatbot_response = GenerateRecommendation(client, game_name).content
        print(final_chatbot_response)
    else:
        print("No model found")

FindRecommendation(client)
