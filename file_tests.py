import spacy
from spacy.tokens import Doc
from SubjectObjectExtractor import SubjectObjectExtractor

nlp = spacy.load("en_core_web_md")
pipeline_component = SubjectObjectExtractor(nlp)
pipeline_component.adj_as_object = True
Doc.set_extension('svos', default=None)
nlp.add_pipe(pipeline_component, last=True)

file = open('text3.txt', 'r')
i = 1
for line in file:
    doc = nlp(line)
    print(i, doc)
    i += 1
    for svo in doc._.svos:
        print('    ', svo)