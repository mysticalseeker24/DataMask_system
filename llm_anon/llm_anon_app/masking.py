import string
import openai
import os
from my_secrets import my_secrets
import json
openai_key = my_secrets.get('openai_key')
openai.api_key = openai_key   
os.environ["OPENAI_API_KEY"] = openai_key

import google.generativeai as genai
genai.configure(api_key=my_secrets.get('gemini_key'))
model = genai.GenerativeModel('gemini-1.5-pro-latest')

def ensemble_choices(ner_dict):
    types = []
    choices = {}
    for name in ner_dict:
        ent_type = ner_dict[name]["entity_type"]
        if ent_type not in types:
            choices[ent_type] = "None"
            types.append(ent_type)

    print("choices: ",choices)
    print("nerdict: ", ner_dict)
    return choices


def complete_masking(entity, word, post_processed_word):
    return_word = ""
    if entity == "PERCENT":
        return_word = "[REDACTED]%"
    else:
        return_word = "[REDACTED]"
    
    return "<b>" + return_word + "</b>"

def perturbing(entity, word, post_processed_word):
    return_word = ""
    if entity == "PERSON":
        return_word = "TODO Perturb: "+entity
    elif entity == "ORGANIZATION":
        return_word = "TODO Perturb: "+entity
    elif entity == "GPE":
        return_word = "TODO Perturb: "+entity
    elif entity == "DATE":
        return_word = "TODO Perturb: "+entity
    elif entity == "TIME":
        return_word = "TODO Perturb: "+entity
    elif entity == "MONEY":
        return_word = "TODO Perturb: "+entity
    elif entity == "PERCENT":
        return_word = "TODO Perturb: "+entity
    elif entity == "QUANTITY":
        return_word = "TODO Perturb: "+entity
    elif entity == "ORDINAL":
        return_word = "TODO Perturb: "+entity
    elif entity == "CARDINAL":
        return_word = "TODO Perturb: "+entity
    elif entity == "LOCATION":
        return_word = "TODO Perturb: "+entity
    else:
        return_word = word

    return "<b>" + return_word + "</b>"

def group_based(entity, word, post_processed_word):
    return_word = ""
    if entity == "PERSON":
        #TODO
        return "TODO group-based: "+entity
    elif entity == "ORGANIZATION":
        #TODO
        return "TODO group-based: "+entity
    elif entity == "GPE":
        #TODO
        return "TODO group-based: "+entity
    elif entity == "DATE":
        #TODO
        return "TODO group-based: "+entity
    elif entity == "TIME":
        #TODO
        return "TODO group-based: "+entity
    elif entity == "MONEY":
        #TODO
        return "TODO group-based: "+entity
    elif entity == "PERCENT":
        num = int(post_processed_word[:-1])
        return str(round(num, -1)) + "%"
    elif entity == "QUANTITY":
        #TODO
        return "TODO group-based: "+entity
    elif entity == "ORDINAL":
        #TODO
       return "TODO group-based: "+entity
    elif entity == "CARDINAL":
        #TODO
        return "TODO group-based: "+entity
    elif entity == "LOCATION'":
        #TODO
        return "TODO group-based: "+entity
    else:
        return word

# "PERSON": "PERTURB",
# "ORGANIZATION": "PERTURB",
# "LOCATION": "GROUP",
# "DATE": "PERTURB",
# "TIME": "PERTURB",
# "MONEY": "GROUP",
# "PERCENT": "GROUP",
# "FACILITY": "PERTURB",
# "GPE": "PERTURB",
# "CARDINAL": "GROUP",
    
def extract_context(text, ner_dict):
    # get all words in ner_dict if entity type is either PERSON, ORGANIZATION, LOCATION, FACILITY, or GPE
    name_entity_types = ["PERSON", "ORGANIZATION", "LOCATION", "FACILITY", "GPE"]
    name_entities = []
    for word in ner_dict:
        if ner_dict[word]["entity_type"] in name_entity_types:
            # print("word: ", word, "  entity_type: ", ner_dict[word]["entity_type"])
            name_entities.append(f"{ner_dict[word]['entity_type']}: {word}")

    example_output_str = "EXAMPLE OUTPUT:\n{<entity #1>: <3 comma-seperated points>, <entity #2>: <3 comma-seperated points>, ...}\n"
    name_entities_str = '\n'.join(name_entities)

    name_prompt = f"You are an anthropology/business/geography expert trying to anonymize names by giving a name generator some generalized context clues (DO NOT INCLUDE THE ACTUAL NAME - WE ARE TRYING TO AVOID LEAKING THAT), please come up with 3 comma-seperated points EACH about the following named entities, please include it in a python dict:\n{name_entities_str}\n\n{example_output_str}\n\nOriginal Text:\n{text}"
    print(name_prompt)

def create_replacements(text, ner_dict, choice_dict):
    # for each word in the ner_dict, create a CONTEXT-DEPENDANT replacement for it (meaning the replacement is based on the context of the word, in relation to the text)
    # get all words in ner_dict and their entities:
    entities_str = ""
    for word in ner_dict:
        entity_type = ner_dict[word]['entity_type']
        entities_str += f"{entity_type} ({choice_dict[entity_type]}): {word}\n"
    
    example_output_str = "EXAMPLE OUTPUT:\n{'john': 'james', '10': '7-15', ...}\n"
    entities_prompt = f"Please come up with a replacement for each of the following named entities, please include it in a python dict:\n{entities_str}\n\n{example_output_str}\n\nOriginal Text:\n{text}\n\nMeaning of masking choices:\nPerturb: Slightly change the entity with something similar (e.g. James to John, or springfield to toledo)\nGroup-based: Replace the entity with a group-based representation (e.g. 17 years old becomes 10-20 years old)\n"

    # print(entities_prompt)
    response = model.generate_content(entities_prompt, generation_config=genai.types.GenerationConfig(temperature=0.0))

    # post process output, getting only the dict part - between { and }
    replacement_dict_text = response.text.split("{")[1].split("}")[0]
    replacement_dict_text = "{" + replacement_dict_text + "}"
    # replace all single quotes with double quotes
    replacement_dict_text = replacement_dict_text.replace("'", "\"")
    # for each line, remove everything after #
    replacement_dict_text = "\n".join([line.split("#")[0] for line in replacement_dict_text.split("\n")])
    print(replacement_dict_text)

    # convert the response to a python dict
    replacements = json.loads(replacement_dict_text)
    return replacements

#TODO create all mask functions
def mask_main(text, ner_dict, choice_dict):
    #print("ner_dict: ", ner_dict, "  choice_dict: ",choice_dict)
    output_text = ""
    extract_context(text, ner_dict)
    replacements = create_replacements(text, ner_dict, choice_dict)

    for paragraph in text.split("\n"):
        for word in paragraph.split():
            post_processed_word = word.lower()
            punc = '''!()-[]{};:'"\,<>./?@#$^&*_~'''

            if word[-1] in punc:
                post_processed_word = post_processed_word[:-1]
            if word[0] == "$":
                post_processed_word = post_processed_word[1:]
            
            if post_processed_word in ner_dict:
                entity = ner_dict[post_processed_word]["entity_type"]
                choice = choice_dict[entity]

                if choice == "Complete Mask":
                    post_masked_word = complete_masking(entity, word, post_processed_word)
                    post_added_word = word.lower().replace(post_processed_word, post_masked_word) 
                    output_text += post_added_word + " "
                elif choice == "Perturb":
                    # post_masked_word = perturbing(entity, word, post_processed_word)
                    post_masked_word = replacements[post_processed_word] if post_processed_word in replacements else post_processed_word
                    post_masked_word = "<b>" + post_masked_word + "</b>"
                    post_added_word = word.lower().replace(post_processed_word, post_masked_word)
                    output_text += post_added_word + " "
                elif choice == "Group-based":
                    post_masked_word = replacements[post_processed_word] if post_processed_word in replacements else post_processed_word
                    post_masked_word = "<b>" + post_masked_word + "</b>"
                    post_added_word = word.lower().replace(post_processed_word, post_masked_word) 
                    output_text += post_added_word + " "
                else:
                    output_text += word + " "
            else:
                output_text += word + " "
        output_text += "\n"

    return output_text