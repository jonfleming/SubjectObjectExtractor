# Introduction to spaCy for NLP and Machine Learning

## Dependencies
spaCy

To install spaCy:
```
pip install spacy
python -m spacy.en.download all
```

## Running the files
python test.py

python file_tests.py

## Using SubjectObjectExtractor
import spacy
from spacy.tokens import Doc
from SubjectObjectExtractor import SubjectObjectExtractor

# Load spacy model
nlp = spacy.load("en_core_web_md")

# Add SubjectObjectExtractor to spacy pipeline
pipeline_component = SubjectObjectExtractor(nlp)
Doc.set_extension('svos', default=None)
nlp.add_pipe(pipeline_component, last=True)

# Treat Adjective as sentence object
pipeline_component.adj_as_object = True

doc = nlp("The car is red.")
_subject, _verb, _object = doc._.svos[0]
print(_subject, _verb, _object)