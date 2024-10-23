# This is the main helper file for named entity recognition (NER) in the LLM Anonymizer app. 
# We're going to get input text and then try/test a few different methods of NER
# Finally, we'll return a dict of found entities and their types.

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

import nltk
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')
from nltk import word_tokenize, pos_tag, ne_chunk

import spacy
import en_core_web_lg

import flair
from flair.data import Sentence
from flair.models import SequenceTagger
from segtok.segmenter import split_single
tagger = SequenceTagger.load("ner")

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine, DeanonymizeEngine, OperatorConfig
from presidio_anonymizer.operators import Operator, OperatorType

from typing import Dict
from pprint import pprint
import requests

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def preprocessing(input_text, lowercase=False):
    # Remove extra newlines
    input_text = input_text.replace("\r", "")
    input_text = input_text.replace("\n", "  ")

    # lowercase the text
    if (lowercase):
        input_text = input_text.lower()

    return input_text

def nltk_ner(input_text):
    entities = []
    for sent in nltk.sent_tokenize(input_text):
        for chunk in nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(sent))):
            if hasattr(chunk, "label"):
                entities.append({"entity": " ".join(c[0] for c in chunk), "entity_type": chunk.label()})
    return entities

def spacy_ner(input_text):
    nlp = en_core_web_lg.load()
    doc = nlp(input_text)
    entities = [{"entity": ent.text, "entity_type": ent.label_} for ent in doc.ents]
    return entities

def flair_ner(input_text):
    entities = []
    for sentence in split_single(input_text):
        sentence = Sentence(sentence)
        tagger.predict(sentence)
        for entity in sentence.get_spans("ner"):
            entities.append({"entity": entity.text, "entity_type": entity.tag})
    return entities

def regex_ner(input_text):
    # specific regex for dates, SSNs, emails, phone numbers, urls, and credit card numbers
    entities = []
    date = re.compile(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}")
    ssn = re.compile(r"\d{3}-\d{2}-\d{4}")
    email = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    phone = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
    url = re.compile(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+")
    cc = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

    for match in date.finditer(input_text):
        entities.append({"entity": match.group(), "entity_type": "DATE"})
    for match in ssn.finditer(input_text):
        entities.append({"entity": match.group(), "entity_type": "SSN"})
    for match in email.finditer(input_text):
        entities.append({"entity": match.group(), "entity_type": "EMAIL"})
    for match in phone.finditer(input_text):
        entities.append({"entity": match.group(), "entity_type": "PHONE"})
    for match in url.finditer(input_text):
        entities.append({"entity": match.group(), "entity_type": "URL"})
    for match in cc.finditer(input_text):
        entities.append({"entity": match.group(), "entity_type": "CREDITCARD"})
    return entities

def presidio_ner(input_text):
    analyzer = AnalyzerEngine()
    results = analyzer.analyze(text=input_text, language="en", entities=["PERSON", "LOCATION", "NRP", "DATE_TIME"], score_threshold=0.5)
    entities = []
    for result in results:
        entity_type = result.entity_type
        if (entity_type == "NRP"):
            entity_type = "GPE"
        elif (entity_type == "DATE_TIME"):
            entity_type = "DATE"
        entities.append({"entity": input_text[result.start:result.end], "entity_type": entity_type})

    return entities

def rename_entities(entities):
    # Following the NTLK convention for entity types: PERSON, ORGANIZATION, LOCATION, DATE, TIME, MONEY, PERCENT, FACILITY, GPE
    for entity in entities:
        if entity["entity_type"] == "PER":
            entity["entity_type"] = "PERSON"
        elif entity["entity_type"] == "ORG":
            entity["entity_type"] = "ORGANIZATION"
        elif entity["entity_type"] == "LOC":
            entity["entity_type"] = "LOCATION"
    return entities

def split_entities(entities):
    # Split the entities by space
    split_entities = []
    for entity_dict in entities:
        for word in entity_dict["entity"].split(" "):
            split_entities.append({"entity": word, "entity_type": entity_dict["entity_type"]})
    return split_entities

def recombine_entities(entities):
    # Recombine the entities by space IF they are next to each other in the original text
    recombined_entities = []
    entity = ""
    entity_type = ""
    for i in range(len(entities)):
        if entity == "":
            entity = entities[i]["entity"]
            entity_type = entities[i]["entity_type"]
        elif entities[i]["entity"] == entity[-1] + " " + entities[i]["entity"]:
            entity += " " + entities[i]["entity"]
        else:
            recombined_entities.append({"entity": entity, "entity_type": entity_type})
            entity = entities[i]["entity"]
            entity_type = entities[i]["entity_type"]
    return recombined_entities

def ensemble_ner(input_text):

    input_text_reg = preprocessing(input_text)
    input_text_lower = preprocessing(input_text, lowercase=True)
    futures_reg = []
    futures_lower = []
    with ThreadPoolExecutor() as executor:
        # Get the entities from all the NER methods (first set)
        futures_reg.append(executor.submit(nltk_ner, input_text_reg))
        futures_reg.append(executor.submit(rename_entities, spacy_ner(input_text_reg)))
        futures_reg.append(executor.submit(rename_entities, flair_ner(input_text_reg)))
        futures_reg.append(executor.submit(regex_ner, input_text_reg))
        futures_reg.append(executor.submit(presidio_ner, input_text_reg))

        # second set with lowercase
        futures_lower.append(executor.submit(nltk_ner, input_text_lower))
        futures_lower.append(executor.submit(rename_entities, spacy_ner(input_text_lower)))
        futures_lower.append(executor.submit(rename_entities, flair_ner(input_text_lower)))
        futures_lower.append(executor.submit(regex_ner, input_text_lower))
        futures_lower.append(executor.submit(presidio_ner, input_text_lower))

    # Retrieve the results
    nltk_entities = futures_reg[0].result() + futures_lower[0].result()
    spacy_entities = futures_reg[1].result() + futures_lower[1].result()
    flair_entities = futures_reg[2].result() + futures_lower[2].result()
    regex_entities = futures_reg[3].result() + futures_lower[3].result()
    presidio_entities = futures_reg[4].result() + futures_lower[4].result()

    # TODO: allow user to select in the future
    # attach NER model to each of the entity dicts
    # for entity in nltk_entities:
    #     entity["model"] = "nltk"
    # for entity in spacy_entities:
    #     entity["model"] = "spacy"
    # for entity in flair_entities:
    #     entity["model"] = "flair"
    # for entity in regex_entities:
    #     entity["model"] = "regex"

    # Combine the entities by splitting each of the entities by space, then only allowing entities that are in at least 2 methods
    entities = nltk_entities + spacy_entities + flair_entities + presidio_entities

    entities = split_entities(entities)
    count = {}
    # lowercase all entities
    entities = [{"entity": entity["entity"].lower(), "entity_type": entity["entity_type"]} for entity in entities]
    # keep only entities that are least 2 characters
    entities = [entity for entity in entities if len(entity["entity"]) >= 2]
    for entity_dict in entities:
        if entity_dict["entity"] in count:
            count[entity_dict["entity"]] = {"entity_type": entity_dict["entity_type"], "count": count[entity_dict["entity"]]["count"] + 1}
        else:
            count[entity_dict["entity"]] = {"entity_type": entity_dict["entity_type"], "count": 1}
    
    # # Method to get all entities that are in at least 2 methods
    # entities = [{"entity": entity, "entity_type": count[entity]["entity_type"]} for entity in count if count[entity]["count"] >= 2]
    # entities += regex_entities
            
    # Add the regex entities to count with an automatic count of 3
    for entity_dict in regex_entities:
        if entity_dict["entity"] in count:
            count[entity_dict["entity"]] = {"entity_type": entity_dict["entity_type"], "count": count[entity_dict["entity"]]["count"] + 3}
        else:
            count[entity_dict["entity"]] = {"entity_type": entity_dict["entity_type"], "count": 3}

    # TODO: fix if we have time! 
    # Finally, combine the words by space IF they are next to each other in the original text
    # print(recombine_entities(entities))

    # return entities
    return count

# Doesn't work well :(
def bert_ner(input_text):
    # Load the model
    model = AutoModelForTokenClassification.from_pretrained("dbmdz/bert-large-cased-finetuned-conll03-english")
    tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")
    
    # Tokenize the input text
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True, padding=True)
    
    # Get the model output
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Get the predicted labels
    predicted = torch.argmax(outputs.logits, dim=2)
    
    # Get the entities
    entities = []
    entity = ""
    entity_type = ""
    for i in range(len(predicted[0])):
        token = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0][i].item())
        label = predicted[0][i].item()
        if label == 1:
            entity += token
            entity_type = "B-PER"
        elif label == 2:
            entity += token
            entity_type = "I-PER"
        elif label == 3:
            entity += token
            entity_type = "B-ORG"
        elif label == 4:
            entity += token
            entity_type = "I-ORG"
        elif label == 5:
            entity += token
            entity_type = "B-LOC"
        elif label == 6:
            entity += token
            entity_type = "I-LOC"
        elif label == 7:
            entity += token
            entity_type = "B-MISC"
        elif label == 8:
            entity += token
            entity_type = "I-MISC"
        else:
            if entity != "":
                entities.append({"entity": entity, "entity_type": entity_type})
                entity = ""
                entity_type = ""
    
    return entities